from __future__ import annotations

import logging
import re
import uuid
from dataclasses import asdict, dataclass

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import RequireAdminOrService
from app.core.config import settings
from app.db.models import ProcessingJob, VideoAsset
from app.db.session import get_db
from app.queue.publisher import publish_processing_job
from app.storage import get_object_store
from app.storage.local_store import UnsafeStorageKey
from app.workers.tasks import run_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES: set[str] = {
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
    "application/octet-stream",
}

# Pipeline expectations: storage_key fits inside the 512-char column.
_MAX_SAFE_FILENAME_LEN = 200
_SIGNED_URL_TTL_MINUTES = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _max_upload_size_bytes() -> int:
    return settings.max_upload_size_mb * 1024 * 1024


def _safe_filename(filename: str | None) -> str:
    """Sanitize an uploaded filename.

    - Strips any directory components (Windows + POSIX).
    - Replaces unsafe characters with ``_``.
    - Preserves a sensible file extension.
    - Caps length so the full storage_key stays within the DB column.
    """
    raw = (filename or "").strip()
    if not raw:
        return "upload.bin"
    base = raw.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]

    if "." in base:
        name, _, ext = base.rpartition(".")
        ext = re.sub(r"[^A-Za-z0-9]", "", ext)[:8]
    else:
        name, ext = base, ""

    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._")
    if not name:
        name = "upload"

    safe = f"{name}.{ext}" if ext else name
    return safe[:_MAX_SAFE_FILENAME_LEN]


def _is_gcs_backend() -> bool:
    return settings.storage_backend == "gcs"


def _build_storage_key(filename: str | None) -> tuple[str, str]:
    """Return ``(video_uuid_hex, storage_key)`` for a fresh upload."""
    safe_name = _safe_filename(filename)
    video_uuid = uuid.uuid4().hex
    storage_key = f"originals/{video_uuid}/{safe_name}"
    return video_uuid, storage_key


def _generate_upload_url(
    storage_key: str,
    content_type: str,
    request: Request,
) -> str:
    """Generate a v4 signed PUT URL (GCS), or a local-dev PUT target otherwise.

    Storage signing failures are translated to a clean HTTP 500 — the underlying
    exception is logged with traceback, but the signed URL itself is never logged.
    """
    store = get_object_store()
    try:
        if _is_gcs_backend():
            return store.generate_signed_upload_url(
                storage_key=storage_key,
                content_type=content_type,
                expires_minutes=_SIGNED_URL_TTL_MINUTES,
            )
        return str(request.url_for("local_direct_put", storage_key=storage_key))
    except Exception:
        logger.exception(
            "upload_init_signing_failed storage_key=%s backend=%s",
            storage_key,
            settings.storage_backend,
        )
        raise HTTPException(
            status_code=500,
            detail="Could not generate signed upload URL",
        )


def _assert_worker_broker_available() -> None:
    """Fail fast when Celery broker is down.

    This prevents jobs from being persisted as "queued" when the queue itself is
    unreachable, which otherwise looks healthy in the UI but never runs.
    """
    if settings.queue_backend not in ("celery", "redis"):
        return
    try:
        with run_pipeline.app.connection_for_write() as conn:
            conn.ensure_connection(max_retries=1)
    except Exception:
        logger.warning("worker queue unavailable; refusing to finalize upload")
        raise HTTPException(
            status_code=503,
            detail="Worker queue unavailable. Please retry shortly.",
        )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UploadInitRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(..., min_length=1, max_length=128)
    size_bytes: int = Field(..., gt=0)
    title: str | None = Field(None, max_length=255)


class UploadCompleteRequest(BaseModel):
    video_id: int
    storage_key: str = Field(..., min_length=1, max_length=512)
    title: str | None = Field(None, max_length=255)


@dataclass
class UploadInitResponse:
    video_id: int
    storage_key: str
    upload_url: str
    upload_method: str
    required_headers: dict[str, str]
    expires_in_seconds: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/uploads/init")
def init_direct_upload(
    _auth: RequireAdminOrService,
    payload: UploadInitRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    if payload.size_bytes > _max_upload_size_bytes():
        raise HTTPException(status_code=413, detail="File too large")

    _video_uuid, storage_key = _build_storage_key(payload.filename)

    logger.info(
        "upload_init_started content_type=%s size_bytes=%s storage_key=%s backend=%s",
        payload.content_type,
        payload.size_bytes,
        storage_key,
        settings.storage_backend,
    )

    # Sign first so storage misconfiguration fails fast without orphaning a row.
    upload_url = _generate_upload_url(
        storage_key=storage_key,
        content_type=payload.content_type,
        request=request,
    )

    video = VideoAsset(
        title=payload.title or payload.filename,
        original_filename=payload.filename,
        status="upload_pending",
        storage_key=storage_key,
        file_size_bytes=payload.size_bytes,
    )
    try:
        db.add(video)
        db.commit()
        db.refresh(video)
    except IntegrityError:
        db.rollback()
        logger.warning("upload_init_conflict storage_key=%s", storage_key)
        raise HTTPException(
            status_code=409,
            detail="Upload asset conflict. Please retry upload initialization.",
        )

    logger.info(
        "upload_init_completed video_id=%s storage_key=%s size_bytes=%s",
        video.id,
        storage_key,
        payload.size_bytes,
    )
    return asdict(
        UploadInitResponse(
            video_id=video.id,
            storage_key=storage_key,
            upload_url=upload_url,
            upload_method="PUT",
            required_headers={"Content-Type": payload.content_type},
            expires_in_seconds=_SIGNED_URL_TTL_MINUTES * 60,
        )
    )


_LOCAL_PUT_KEY_PREFIXES = ("originals/",)


@router.put("/uploads/direct/{storage_key:path}", name="local_direct_put")
async def local_direct_put(storage_key: str, request: Request) -> Response:
    """Local-development direct-PUT target.

    Mimics the contract of a GCS signed-URL upload so the same client code
    works against both backends. Disabled in production GCS deployments.

    Hardened against path traversal: keys must start with the canonical
    ``originals/`` prefix and contain no ``..`` / absolute / backslash
    segments. ``LocalStore`` enforces the same invariants defensively.
    """
    if _is_gcs_backend():
        raise HTTPException(
            status_code=400,
            detail="Use the signed GCS URL for direct uploads",
        )
    if not storage_key.startswith(_LOCAL_PUT_KEY_PREFIXES):
        logger.warning("local_direct_put_rejected_prefix storage_key=%s", storage_key)
        raise HTTPException(status_code=400, detail="Invalid storage key prefix")
    body = await request.body()
    if len(body) > _max_upload_size_bytes():
        raise HTTPException(
            status_code=413,
            detail="File too large for direct upload route",
        )
    store = get_object_store()
    content_type = request.headers.get("content-type")
    try:
        store.upload_bytes(storage_key, body, content_type=content_type)
    except UnsafeStorageKey:
        logger.warning("local_direct_put_rejected_key storage_key=%s", storage_key)
        raise HTTPException(status_code=400, detail="Invalid storage key")
    logger.info("local_direct_put storage_key=%s bytes=%s", storage_key, len(body))
    return Response(status_code=200)


@router.post("/uploads/complete")
def complete_direct_upload(
    _auth: RequireAdminOrService,
    payload: UploadCompleteRequest,
    db: Session = Depends(get_db),
):
    """Finalize a previously initialized upload.

    The ``storage_key`` in the request body is treated as a confirmation,
    NOT as authoritative data. It must match the row that ``init`` reserved
    for the given ``video_id``; otherwise we refuse with HTTP 409 to prevent
    one client from re-pointing another client's row at a different object.
    Idempotent on retries: if the row is already ``uploaded`` and a job
    exists, we return the existing job_id without creating a duplicate.
    """
    video = db.get(VideoAsset, payload.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.storage_key != payload.storage_key:
        logger.warning(
            "upload_complete_storage_key_mismatch video_id=%s row_key=%s body_key=%s",
            video.id,
            video.storage_key,
            payload.storage_key,
        )
        raise HTTPException(
            status_code=409,
            detail="storage_key does not match the initialized upload",
        )

    store = get_object_store()
    if not store.object_exists(video.storage_key):
        raise HTTPException(
            status_code=400,
            detail="Uploaded object not found in storage",
        )

    metadata = store.get_object_metadata(video.storage_key) or {}
    if metadata.get("size"):
        video.file_size_bytes = int(metadata["size"])
    if payload.title:
        video.title = payload.title

    _assert_worker_broker_available()

    # Idempotency: if a job already exists for this video, return it.
    existing_job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.video_id == video.id)
        .order_by(ProcessingJob.id.desc())
        .first()
    )
    if existing_job is not None and video.status == "uploaded":
        logger.info(
            "upload_complete_idempotent video_id=%s job_id=%s",
            video.id,
            existing_job.id,
        )
        return {
            "video_id": video.id,
            "job_id": existing_job.id,
            "status": existing_job.status or "queued",
        }

    video.status = "uploaded"
    job = ProcessingJob(video_id=video.id, status="queued", current_stage="queued")
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning(
            "upload_complete_conflict video_id=%s storage_key=%s",
            video.id,
            video.storage_key,
        )
        raise HTTPException(
            status_code=409,
            detail="Upload completion conflict. The video may already be finalized.",
        )
    db.refresh(job)
    try:
        publish_processing_job(job.id)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Job created, but dispatch failed. Please retry shortly.",
        )

    logger.info(
        "upload_complete_completed video_id=%s job_id=%s storage_key=%s",
        video.id,
        job.id,
        video.storage_key,
    )
    return {"video_id": video.id, "job_id": job.id, "status": "queued"}


@router.post("/videos/upload", deprecated=True)
async def upload_video(
    _auth: RequireAdminOrService,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Legacy small-file upload — kept for local/dev only.

    For production-sized assets, clients must use the signed-URL flow:
    ``POST /api/uploads/init`` -> direct PUT -> ``POST /api/uploads/complete``.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    data = await file.read()
    if len(data) > _max_upload_size_bytes():
        raise HTTPException(
            status_code=413,
            detail="Large video uploads must use signed GCS upload flow.",
        )

    safe_name = _safe_filename(file.filename)
    video_uuid = uuid.uuid4().hex
    key = f"originals/{video_uuid}/{safe_name}"

    get_object_store().upload_bytes(key, data, content_type=file.content_type)
    video = VideoAsset(
        title=title or file.filename,
        original_filename=file.filename or safe_name,
        storage_key=key,
        status="uploaded",
        file_size_bytes=len(data),
    )
    db.add(video)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("legacy_upload_conflict storage_key=%s", key)
        raise HTTPException(
            status_code=409,
            detail="Upload asset conflict. Please retry upload.",
        )
    db.refresh(video)

    _assert_worker_broker_available()

    job = ProcessingJob(video_id=video.id, status="queued", current_stage="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        publish_processing_job(job.id)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Job created, but dispatch failed. Please retry shortly.",
        )
    return {"video_id": video.id, "job_id": job.id}

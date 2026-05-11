from __future__ import annotations

import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.api.pagination import paginate_sa_query
from app.core.auth import RequireReviewerOrAdmin
from app.core.config import settings
from app.db.models import (
    AuditLog,
    FrameSample,
    GeneratedTag,
    ProcessingJob,
    SceneSegment,
    Transcript,
    VideoAsset,
)
from app.db.session import get_db
from app.storage import get_object_store
from app.storage.local_store import LocalStore, UnsafeStorageKey

router = APIRouter(prefix="/videos")
logger = logging.getLogger(__name__)

# Cost lever: short TTL keeps signed URLs from leaking into long-lived caches
# or share links. The browser only needs the URL for the current viewing
# session; on refresh the frontend re-asks the API, which is cheap.
_PLAYBACK_URL_TTL_SECONDS = 60 * 60  # 1 hour
_POSTER_URL_TTL_SECONDS = 60 * 60

# Range streaming chunk size for the local-dev stream endpoint. 1 MiB is a
# good balance between syscall overhead and per-chunk memory.
_STREAM_CHUNK_BYTES = 1024 * 1024

# Statuses where the original media object is guaranteed not to exist yet.
# We refuse playback rather than returning a URL that would 404 from GCS.
_NON_PLAYABLE_VIDEO_STATUSES = {"upload_pending", "failed"}


def _is_gcs_backend() -> bool:
    return settings.storage_backend == "gcs"


def _guess_video_content_type(storage_key: str | None) -> str:
    """Best-effort MIME for the original asset.

    The HTML5 ``<video>`` element tolerates a missing/wrong type as long as
    the bytes are valid, but a correct type lets the browser decide whether
    it can play the file before it issues a Range request.
    """
    if storage_key:
        guessed, _ = mimetypes.guess_type(storage_key)
        if guessed and guessed.startswith("video/"):
            return guessed
    return "video/mp4"


def _serialize_video(video: VideoAsset, db: Session) -> dict[str, Any]:
    tags = db.query(GeneratedTag).filter_by(video_id=video.id).all()
    job = (
        db.query(ProcessingJob)
        .filter_by(video_id=video.id)
        .order_by(ProcessingJob.id.desc())
        .first()
    )
    transcript = db.query(Transcript).filter_by(video_id=video.id).first()
    approved_or_pending = [t for t in tags if t.status in ("approved", "pending_review")]
    # Prefer the LLM-generated summary (first-class field) and fall back to a
    # transcript snippet only when the pipeline has not yet produced one.
    description = (
        getattr(video, "summary", None)
        or (transcript.text[:300] if transcript else None)
    )
    return {
        "id": video.id,
        "title": video.title,
        "description": description,
        "summary": getattr(video, "summary", None),
        "duration_seconds": video.duration_seconds,
        "status": video.status,
        "tags": [
            {
                "value": tag.tag_value,
                "type": tag.tag_type,
                "confidence": tag.confidence,
            }
            for tag in approved_or_pending
        ],
        "genres": sorted(
            {tag.tag_value for tag in approved_or_pending if tag.tag_type == "genre"}
        ),
        "moods": sorted(
            {tag.tag_value for tag in approved_or_pending if tag.tag_type == "mood"}
        ),
        "confidence": max(
            (tag.confidence or 0.0 for tag in approved_or_pending),
            default=None,
        ),
        "processingStage": job.current_stage if job else None,
        "width": video.width,
        "height": video.height,
        "codec": video.codec,
        "bitrate": video.bitrate,
        "frame_rate": video.frame_rate,
        "file_size_bytes": video.file_size_bytes,
        "created_at": video.created_at.isoformat() if video.created_at else None,
        "updated_at": video.updated_at.isoformat() if video.updated_at else None,
        "storage_key": video.storage_key,
    }


@router.get("")
def list_videos(
    db: Session = Depends(get_db),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    status: str | None = None,
    genre: str | None = None,
    mood: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    title_contains: str | None = None,
):
    q = db.query(VideoAsset)
    if status:
        q = q.filter(VideoAsset.status == status)
    if title_contains:
        q = q.filter(VideoAsset.title.ilike(f"%{title_contains}%"))
    if created_after:
        try:
            dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
            q = q.filter(VideoAsset.created_at >= dt)
        except ValueError:
            raise HTTPException(400, detail="invalid created_after datetime") from None
    if created_before:
        try:
            dt = datetime.fromisoformat(created_before.replace("Z", "+00:00"))
            q = q.filter(VideoAsset.created_at <= dt)
        except ValueError:
            raise HTTPException(400, detail="invalid created_before datetime") from None
    if genre:
        q = q.filter(
            exists().where(
                GeneratedTag.video_id == VideoAsset.id,
                GeneratedTag.tag_type == "genre",
                GeneratedTag.tag_value == genre,
            )
        )
    if mood:
        q = q.filter(
            exists().where(
                GeneratedTag.video_id == VideoAsset.id,
                GeneratedTag.tag_type == "mood",
                GeneratedTag.tag_value == mood,
            )
        )
    q = q.order_by(VideoAsset.id.desc())
    raw = paginate_sa_query(q, page=page, page_size=page_size)
    return {
        "items": [_serialize_video(v, db) for v in raw["items"]],
        "page": raw["page"],
        "page_size": raw["page_size"],
        "total": raw["total"],
        "has_next": raw["has_next"],
    }


@router.get("/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(VideoAsset, video_id)
    if not video:
        raise HTTPException(404)
    return _serialize_video(video, db)


@router.get("/{video_id}/frames")
def frames(video_id: int, db: Session = Depends(get_db)):
    return db.query(FrameSample).filter_by(video_id=video_id).all()


@router.get("/{video_id}/scenes")
def scenes(video_id: int, db: Session = Depends(get_db)):
    return db.query(SceneSegment).filter_by(video_id=video_id).all()


@router.get("/{video_id}/transcript")
def transcript(video_id: int, db: Session = Depends(get_db)):
    return db.query(Transcript).filter_by(video_id=video_id).first()


@router.get("/{video_id}/tags")
def tags(video_id: int, db: Session = Depends(get_db)):
    return db.query(GeneratedTag).filter_by(video_id=video_id).all()


@router.post("/{video_id}/publish")
def publish_video(
    video_id: int,
    _auth: RequireReviewerOrAdmin,
    db: Session = Depends(get_db),
):
    """Mark a reviewed video as published.

    Requires that no auto-generated tags are still in pending_review and
    that the video has at least one approved tag, so a human has actually
    signed off on the AI output before it goes live.
    """
    video = db.get(VideoAsset, video_id)
    if not video:
        raise HTTPException(404, "video not found")
    if video.status not in ("review_ready", "published"):
        raise HTTPException(
            409,
            f"video is in status {video.status!r}; only review_ready videos can be published",
        )
    pending = (
        db.query(GeneratedTag)
        .filter_by(video_id=video_id, status="pending_review")
        .count()
    )
    if pending:
        raise HTTPException(
            409,
            f"{pending} tag(s) are still pending review; resolve them before publishing",
        )
    approved = (
        db.query(GeneratedTag)
        .filter_by(video_id=video_id, status="approved")
        .count()
    )
    if approved == 0:
        raise HTTPException(
            409,
            "video has no approved tags; approve at least one tag before publishing",
        )

    before_status = video.status
    video.status = "published"
    db.add(
        AuditLog(
            actor="reviewer",
            action="video_publish",
            entity_type="video",
            entity_id=video.id,
            before_json={"status": before_status},
            after_json={"status": "published"},
        )
    )
    db.commit()
    db.refresh(video)
    return _serialize_video(video, db)


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------
#
# Cost & UX rationale
# -------------------
# We deliberately serve the *original* MP4 directly from object storage via a
# short-lived signed URL, rather than transcoding to HLS/DASH. For the size of
# this project the trade-offs land here:
#
# * Transcoding costs (Cloud Transcoder / ffmpeg in the worker) and the 3-5x
#   storage multiplier of multi-bitrate variants dwarf the bandwidth savings.
# * GCS supports HTTP Range requests natively, so the browser's <video> tag
#   can seek without downloading the whole file. That's the seek smoothness.
# * The browser fetches bytes straight from GCS; no Cloud Run egress, so we
#   pay only standard object-storage egress (and can drop a Cloud CDN in
#   front later without changing this code).
# * Signed URLs prevent unrestricted public access — a public bucket would
#   make every video hot-linkable and turn one viral asset into a real bill.
#
# In local dev (``storage_backend != gcs``) the signed URL would be unusable
# from a browser (it's a ``local-storage://`` placeholder), so the playback
# response points at the streaming endpoint below, which serves bytes from
# ``LocalStore`` with Range support so seeking still works.


@router.get("/{video_id}/playback")
def get_playback(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Return a short-lived URL the browser can play directly.

    Response shape:
        {
          "url": str,                 # MP4 source for <video src=...>
          "content_type": str,
          "expires_in_seconds": int,
          "poster_url": str | None,   # optional thumbnail (sampled frame)
          "duration_seconds": float | None,
          "file_size_bytes": int | None,
        }
    """
    video = db.get(VideoAsset, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.storage_key:
        raise HTTPException(status_code=409, detail="Video has no stored asset")
    if video.status in _NON_PLAYABLE_VIDEO_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Video is not playable in status {video.status!r}",
        )

    store = get_object_store()
    if not store.object_exists(video.storage_key):
        # Common when the upload was initialized but the PUT never completed.
        raise HTTPException(
            status_code=409,
            detail="Original media is not present in storage yet",
        )

    if _is_gcs_backend():
        try:
            playback_url = store.generate_signed_url(
                video.storage_key,
                expiration_seconds=_PLAYBACK_URL_TTL_SECONDS,
                method="GET",
            )
        except Exception:
            # Never log the URL itself; only the failure context.
            logger.exception(
                "playback_signing_failed video_id=%s storage_key=%s",
                video.id,
                video.storage_key,
            )
            raise HTTPException(
                status_code=500,
                detail="Could not generate playback URL",
            )
    else:
        playback_url = str(request.url_for("video_stream", video_id=video.id))

    poster_url: str | None = None
    first_frame = (
        db.query(FrameSample)
        .filter_by(video_id=video.id)
        .order_by(FrameSample.timestamp_seconds.asc())
        .first()
    )
    if first_frame and first_frame.storage_key:
        try:
            if _is_gcs_backend():
                poster_url = store.generate_signed_url(
                    first_frame.storage_key,
                    expiration_seconds=_POSTER_URL_TTL_SECONDS,
                    method="GET",
                )
            else:
                poster_url = str(
                    request.url_for("frame_stream", frame_id=first_frame.id)
                )
        except Exception:
            # Poster is best-effort — never block playback on a thumbnail.
            logger.warning(
                "poster_url_failed video_id=%s frame_id=%s",
                video.id,
                first_frame.id,
                exc_info=True,
            )

    return {
        "url": playback_url,
        "content_type": _guess_video_content_type(video.storage_key),
        "expires_in_seconds": _PLAYBACK_URL_TTL_SECONDS,
        "poster_url": poster_url,
        "duration_seconds": video.duration_seconds,
        "file_size_bytes": video.file_size_bytes,
    }


# ---------------------------------------------------------------------------
# Local-dev streaming with HTTP Range support
# ---------------------------------------------------------------------------
#
# In production this endpoint is unused: the playback URL points straight at
# GCS so Cloud Run never sees the video bytes. Locally, the same UI needs a
# real HTTP source, so we serve from ``LocalStore`` honoring Range headers
# (otherwise the <video> tag downloads the whole file before it can seek).


def _parse_range_header(value: str, file_size: int) -> tuple[int, int] | None:
    """Parse a single ``bytes=start-end`` range. Returns ``None`` if invalid.

    We deliberately support only single-range requests; multipart/byteranges
    is not needed by browser <video> elements in practice.
    """
    if not value or not value.startswith("bytes="):
        return None
    spec = value[len("bytes=") :].split(",")[0].strip()
    if "-" not in spec:
        return None
    start_str, end_str = spec.split("-", 1)
    try:
        if start_str == "":
            # Suffix range: last N bytes.
            suffix = int(end_str)
            if suffix <= 0:
                return None
            start = max(file_size - suffix, 0)
            end = file_size - 1
        else:
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
    except ValueError:
        return None
    if start < 0 or end < start or start >= file_size:
        return None
    end = min(end, file_size - 1)
    return start, end


def _iter_file_range(path: Path, start: int, length: int):
    """Yield ``length`` bytes from ``path`` starting at ``start`` in chunks."""
    remaining = length
    with path.open("rb") as fh:
        fh.seek(start)
        while remaining > 0:
            chunk = fh.read(min(_STREAM_CHUNK_BYTES, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _local_path_for_key(storage_key: str) -> Path:
    """Resolve a storage key to a local file path safely.

    Reuses the ``LocalStore`` traversal guards so we never serve a path
    outside the configured store, even if a malformed key reaches this point.
    """
    store = LocalStore()
    return store._resolve_safe(storage_key)  # noqa: SLF001 (intentional reuse)


@router.get("/{video_id}/stream", name="video_stream")
def stream_video(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Range-aware streaming of the original MP4 (local dev only)."""
    if _is_gcs_backend():
        # Production should always go via the signed URL returned by /playback.
        # Refusing here surfaces misconfiguration loudly instead of silently
        # routing all video traffic through Cloud Run.
        raise HTTPException(
            status_code=400,
            detail="Stream endpoint is disabled when GCS backend is active",
        )

    video = db.get(VideoAsset, video_id)
    if not video or not video.storage_key:
        raise HTTPException(status_code=404, detail="Video not found")
    try:
        path = _local_path_for_key(video.storage_key)
    except UnsafeStorageKey:
        raise HTTPException(status_code=400, detail="Invalid storage key")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Media file not found")

    file_size = path.stat().st_size
    content_type = _guess_video_content_type(video.storage_key)

    range_header = request.headers.get("range")
    if range_header:
        parsed = _parse_range_header(range_header, file_size)
        if parsed is None:
            return StreamingResponse(
                iter(()),
                status_code=416,
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        start, end = parsed
        length = end - start + 1
        return StreamingResponse(
            _iter_file_range(path, start, length),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Cache-Control": "private, max-age=0, no-store",
            },
        )

    # Full-file response. Still chunked so a multi-GB file does not load
    # into memory at once.
    return StreamingResponse(
        _iter_file_range(path, 0, file_size),
        media_type=content_type,
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=0, no-store",
        },
    )


@router.get("/frames/{frame_id}/image", name="frame_stream")
def stream_frame_image(
    frame_id: int,
    db: Session = Depends(get_db),
):
    """Serve a sampled frame as the poster image (local dev only).

    In GCS deployments the poster URL is a signed GCS URL and this endpoint
    is not reached.
    """
    if _is_gcs_backend():
        raise HTTPException(
            status_code=400,
            detail="Frame stream endpoint is disabled when GCS backend is active",
        )
    frame = db.get(FrameSample, frame_id)
    if not frame or not frame.storage_key:
        raise HTTPException(status_code=404, detail="Frame not found")
    try:
        path = _local_path_for_key(frame.storage_key)
    except UnsafeStorageKey:
        raise HTTPException(status_code=400, detail="Invalid storage key")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Frame image not found")

    media_type, _ = mimetypes.guess_type(frame.storage_key)
    if not media_type or not media_type.startswith("image/"):
        media_type = "image/jpeg"

    return StreamingResponse(
        _iter_file_range(path, 0, path.stat().st_size),
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=300"},
    )

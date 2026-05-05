from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ProcessingJob, VideoAsset
from app.db.session import get_db
from app.storage import get_object_store
from app.workers.tasks import run_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/x-matroska", "application/octet-stream"}


def _max_upload_size_bytes() -> int:
    return settings.max_upload_size_mb * 1024 * 1024


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", filename).strip("._")
    return cleaned or "upload.bin"


class UploadInitRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    title: str | None = None


class UploadCompleteRequest(BaseModel):
    video_id: int
    storage_key: str
    title: str | None = None


@dataclass
class UploadInitResponse:
    video_id: int
    storage_key: str
    upload_url: str
    upload_method: str
    required_headers: dict[str, str]
    expires_in_seconds: int


@router.post('/uploads/init')
def init_direct_upload(payload: UploadInitRequest, db: Session = Depends(get_db)):
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail='Unsupported file type')
    if payload.size_bytes <= 0:
        raise HTTPException(status_code=400, detail='size_bytes must be greater than 0')
    if payload.size_bytes > _max_upload_size_bytes():
        raise HTTPException(status_code=413, detail='File too large')

    video = VideoAsset(
        title=payload.title,
        original_filename=payload.filename,
        status='upload_pending',
        storage_key=f"pending/{_safe_filename(payload.filename)}",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    storage_key = f"originals/{video.id}/{_safe_filename(payload.filename)}"
    upload_url = get_object_store().generate_signed_upload_url(storage_key=storage_key, content_type=payload.content_type, expires_minutes=15)

    logger.info('upload_init video_id=%s storage_key=%s size_bytes=%s', video.id, storage_key, payload.size_bytes)
    return asdict(
        UploadInitResponse(
            video_id=video.id,
            storage_key=storage_key,
            upload_url=upload_url,
            upload_method='PUT',
            required_headers={'Content-Type': payload.content_type},
            expires_in_seconds=900,
        )
    )


@router.post('/uploads/complete')
def complete_direct_upload(payload: UploadCompleteRequest, db: Session = Depends(get_db)):
    store = get_object_store()
    if not store.object_exists(payload.storage_key):
        raise HTTPException(status_code=400, detail='Uploaded object not found in Cloud Storage')

    video = db.get(VideoAsset, payload.video_id)
    if not video:
        raise HTTPException(status_code=404, detail='Video not found')

    metadata = store.get_object_metadata(payload.storage_key)
    video.storage_key = payload.storage_key
    video.status = 'uploaded'
    video.file_size_bytes = int(metadata.get('size', 0)) if metadata.get('size') else video.file_size_bytes
    if payload.title:
        video.title = payload.title

    job = ProcessingJob(video_id=video.id, status='queued', current_stage='queued')
    db.add(job)
    db.commit()
    db.refresh(job)
    run_pipeline.delay(job.id)

    logger.info('upload_complete video_id=%s job_id=%s storage_key=%s', video.id, job.id, payload.storage_key)
    return {'video_id': video.id, 'job_id': job.id, 'status': 'queued'}


@router.post('/videos/upload', deprecated=True)
async def upload_video(file: UploadFile = File(...), title: str | None = Form(None), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail='Unsupported file type')
    data = await file.read()
    if len(data) > _max_upload_size_bytes():
        raise HTTPException(status_code=413, detail='Large video uploads must use signed GCS upload flow.')
    key = f'videos/{file.filename}'
    get_object_store().upload_bytes(key, data, content_type=file.content_type)
    video = VideoAsset(title=title, original_filename=file.filename, storage_key=key, file_size_bytes=len(data))
    db.add(video)
    db.commit()
    db.refresh(video)
    job = ProcessingJob(video_id=video.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    run_pipeline.delay(job.id)
    return {'video_id': video.id, 'job_id': job.id}

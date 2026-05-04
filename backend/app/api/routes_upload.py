from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import ProcessingJob, VideoAsset
from app.db.session import get_db
from app.storage import get_object_store
from app.workers.tasks import run_pipeline
from app.core.config import settings

router = APIRouter()


@router.post('/videos/upload')
async def upload_video(file: UploadFile = File(...), title: str | None = Form(None), db: Session = Depends(get_db)):
    if file.content_type not in {'video/mp4', 'video/quicktime', 'video/x-matroska', 'application/octet-stream'}:
        raise HTTPException(status_code=400, detail='Unsupported file type')
    data = await file.read()
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail='File too large')
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

from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import VideoAsset, ProcessingJob
from app.storage.local_store import LocalStore
from app.workers.tasks import run_pipeline

router = APIRouter()
@router.post('/videos/upload')
async def upload_video(file: UploadFile = File(...), title: str | None = Form(None), db: Session = Depends(get_db)):
    data = await file.read()
    key = f"videos/{file.filename}"
    LocalStore().put_bytes(key, data)
    video = VideoAsset(title=title, original_filename=file.filename, storage_key=key, file_size_bytes=len(data))
    db.add(video); db.commit(); db.refresh(video)
    job = ProcessingJob(video_id=video.id)
    db.add(job); db.commit(); db.refresh(job)
    run_pipeline.delay(job.id)
    return {"video_id": video.id, "job_id": job.id}

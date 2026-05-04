from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import ProcessingJob
from app.workers.tasks import run_pipeline
router = APIRouter(prefix='/jobs')
@router.get('')
def list_jobs(db: Session = Depends(get_db)): return db.query(ProcessingJob).all()
@router.get('/{job_id}')
def get_job(job_id:int, db:Session=Depends(get_db)):
    job=db.get(ProcessingJob,job_id)
    if not job: raise HTTPException(404)
    return job
@router.post('/{job_id}/retry')
def retry_job(job_id:int, db:Session=Depends(get_db)):
    job=db.get(ProcessingJob,job_id)
    if not job: raise HTTPException(404)
    job.retry_count +=1; db.commit(); run_pipeline.delay(job_id)
    return {"status":"retried"}

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import ProcessingJob
from app.db.session import get_db
from app.workers.tasks import run_pipeline

router = APIRouter(prefix='/jobs')
logger = logging.getLogger(__name__)


@router.get('')
def list_jobs(db: Session = Depends(get_db)):
    return db.query(ProcessingJob).all()


@router.get('/{job_id}')
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job


@router.post('/{job_id}/retry')
def retry_job(job_id: int, db: Session = Depends(get_db)):
    """Retry a previously failed/partial job.

    Behavior:
    - Increments ``retry_count`` and resets ``status='queued'`` so the Jobs UI
      reflects the requeue immediately.
    - Clears the prior ``error_message`` so the operator sees a clean slate.
    - Tolerates a broker outage: if Celery cannot enqueue, the row stays in
      ``queued`` and we surface HTTP 503 instead of leaking a 500. The retry
      counter has already been bumped — this is intentional so the operator
      can see the attempt.
    """
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')

    job.retry_count = (job.retry_count or 0) + 1
    job.status = 'queued'
    job.current_stage = 'queued'
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    db.commit()
    db.refresh(job)

    try:
        run_pipeline.delay(job_id)
    except Exception:
        logger.warning(
            'retry_job_broker_unavailable job_id=%s; row reset but task not enqueued',
            job_id,
        )
        raise HTTPException(
            status_code=503,
            detail='Retry recorded but the worker queue is unavailable. The job will be picked up when the queue recovers.',
        )

    logger.info(
        'retry_job_enqueued job_id=%s retry_count=%s', job_id, job.retry_count
    )
    return {'status': 'retried', 'job_id': job_id, 'retry_count': job.retry_count}

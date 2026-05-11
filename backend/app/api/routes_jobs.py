from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.pagination import paginate_sa_query
from app.core.auth import RequireAdminOrService
from app.db.models import AuditLog, ProcessingJob, ProcessingStageRun, VideoAsset
from app.db.session import get_db
from app.queue.publisher import publish_processing_job

router = APIRouter(prefix='/jobs')
logger = logging.getLogger(__name__)


def _iso(value):
    return value.isoformat() if value else None


def _serialize_stage(run: ProcessingStageRun) -> dict[str, Any]:
    return {
        'id': run.id,
        'job_id': run.job_id,
        'stage_name': run.stage_name,
        'status': run.status,
        'started_at': _iso(run.started_at),
        'completed_at': _iso(run.completed_at),
        'duration_ms': run.duration_ms,
        'error_message': run.error_message,
    }


def _serialize_job(job: ProcessingJob, db: Session) -> dict[str, Any]:
    video = db.get(VideoAsset, job.video_id)
    runs = (
        db.query(ProcessingStageRun)
        .filter_by(job_id=job.id)
        .order_by(ProcessingStageRun.id.asc())
        .all()
    )
    return {
        'id': job.id,
        'video_id': job.video_id,
        'video_title': video.title if video else None,
        'status': job.status,
        'current_stage': job.current_stage,
        'error_message': job.error_message,
        'retry_count': job.retry_count,
        'started_at': _iso(job.started_at),
        'completed_at': _iso(job.completed_at),
        'created_at': _iso(job.created_at),
        'updated_at': _iso(job.updated_at),
        'stage_runs': [_serialize_stage(run) for run in runs],
    }


@router.get('')
def list_jobs(
    db: Session = Depends(get_db),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    status: str | None = None,
    current_stage: str | None = None,
    video_id: int | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
):
    from datetime import datetime

    q = db.query(ProcessingJob)
    if status:
        q = q.filter(ProcessingJob.status == status)
    if current_stage:
        q = q.filter(ProcessingJob.current_stage == current_stage)
    if video_id is not None:
        q = q.filter(ProcessingJob.video_id == video_id)
    if created_after:
        try:
            dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
            q = q.filter(ProcessingJob.created_at >= dt)
        except ValueError:
            raise HTTPException(400, detail="invalid created_after datetime") from None
    if created_before:
        try:
            dt = datetime.fromisoformat(created_before.replace("Z", "+00:00"))
            q = q.filter(ProcessingJob.created_at <= dt)
        except ValueError:
            raise HTTPException(400, detail="invalid created_before datetime") from None
    q = q.order_by(ProcessingJob.id.desc())
    raw = paginate_sa_query(q, page=page, page_size=page_size)
    return {
        "items": [_serialize_job(job, db) for job in raw["items"]],
        "page": raw["page"],
        "page_size": raw["page_size"],
        "total": raw["total"],
        "has_next": raw["has_next"],
    }


@router.get('/{job_id}')
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return _serialize_job(job, db)


@router.get('/{job_id}/stages')
def get_job_stages(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    runs = (
        db.query(ProcessingStageRun)
        .filter_by(job_id=job_id)
        .order_by(ProcessingStageRun.id.asc())
        .all()
    )
    return [_serialize_stage(run) for run in runs]


@router.post('/{job_id}/retry')
def retry_job(
    job_id: int,
    _auth: RequireAdminOrService,
    db: Session = Depends(get_db),
):
    """Retry a previously failed/partial job.

    Behavior:
    - Increments ``retry_count`` and resets ``status='queued'`` so the Jobs UI
      reflects the requeue immediately.
    - Preserves ``current_stage`` when possible, allowing the worker to resume
      from the failed/partial stage instead of replaying all prior outputs.
    - Clears the prior ``error_message`` so the operator sees a clean slate.
    - Tolerates a broker outage: if Celery cannot enqueue, the row stays in
      ``queued`` and we surface HTTP 503 instead of leaking a 500. The retry
      counter has already been bumped — this is intentional so the operator
      can see the attempt.
    """
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')

    prev_err = job.error_message
    prev_status = job.status
    old_retry = job.retry_count or 0
    resume_stage = job.current_stage or 'metadata_extraction'
    job.retry_count = old_retry + 1
    job.status = 'queued'
    job.current_stage = resume_stage
    job.error_message = None
    job.started_at = job.started_at
    job.completed_at = None
    db.add(
        AuditLog(
            actor='api',
            action='processing_job_retry',
            entity_type='processing_job',
            entity_id=job.id,
            before_json={
                'error_message': prev_err,
                'retry_count': old_retry,
                'status': prev_status,
            },
            after_json={
                'retry_count': job.retry_count,
                'status': job.status,
                'retry_reason': 'api_retry',
            },
        )
    )
    db.commit()
    db.refresh(job)

    try:
        publish_processing_job(job_id)
    except Exception:
        logger.warning(
            'retry_job_publish_unavailable job_id=%s; row reset but task not enqueued',
            job_id,
        )
        raise HTTPException(
            status_code=503,
            detail='Retry recorded but queue dispatch is unavailable. Please retry shortly.',
        )

    logger.info(
        'retry_job_enqueued job_id=%s retry_count=%s', job_id, job.retry_count
    )
    return {'status': 'retried', 'job_id': job_id, 'retry_count': job.retry_count}

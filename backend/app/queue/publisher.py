from __future__ import annotations

import logging

from app.core.config import settings
from app.observability.metrics import queue_publish_total
from app.queue.celery_publisher import publish_celery_job
from app.queue.pubsub_publisher import publish_pubsub_job

logger = logging.getLogger(__name__)


def publish_processing_job(job_id: int) -> None:
    backend = settings.queue_backend
    try:
        if backend in ("celery", "redis"):
            publish_celery_job(job_id)
        elif backend == "pubsub":
            publish_pubsub_job(job_id)
        else:
            raise ValueError(f"Unsupported queue backend: {backend}")
        queue_publish_total.labels(backend=backend, status="success").inc()
        logger.info("queue_publish_succeeded job_id=%s queue_backend=%s", job_id, backend)
    except Exception as exc:
        queue_publish_total.labels(backend=backend, status="error").inc()
        logger.exception(
            "queue_publish_failed job_id=%s queue_backend=%s reason=%s",
            job_id,
            backend,
            str(exc),
        )
        raise

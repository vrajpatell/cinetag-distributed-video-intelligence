from __future__ import annotations

import json
import logging

from app.core.config import settings
from app.queue.events import build_processing_job_event

logger = logging.getLogger(__name__)


def publish_pubsub_job(job_id: int) -> None:
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(settings.gcp_project_id, settings.pubsub_topic_name)
    event = build_processing_job_event(job_id)
    data = json.dumps(event).encode("utf-8")
    attrs = {
        "event_type": event["event_type"],
        "job_id": str(job_id),
        "source": str(event["source"]),
        "schema_version": str(event["schema_version"]),
    }

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            future = publisher.publish(topic_path, data, **attrs)
            message_id = future.result(timeout=10)
            logger.info(
                "pubsub_publish_succeeded job_id=%s message_id=%s attempt=%s",
                job_id,
                message_id,
                attempt + 1,
            )
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "pubsub_publish_retry job_id=%s attempt=%s error=%s",
                job_id,
                attempt + 1,
                type(exc).__name__,
            )
    assert last_exc is not None
    raise last_exc

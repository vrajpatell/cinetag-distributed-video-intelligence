from __future__ import annotations

import json

from app.core.config import settings


def publish_pubsub_job(job_id: int) -> None:
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(settings.gcp_project_id, settings.pubsub_topic_name)
    event = {
        "event_type": "processing_job.created",
        "job_id": job_id,
        "source": "cinetag-api",
    }
    future = publisher.publish(topic_path, json.dumps(event).encode("utf-8"))
    future.result(timeout=10)

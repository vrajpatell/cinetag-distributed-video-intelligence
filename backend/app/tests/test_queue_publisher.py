from __future__ import annotations

import json
import types
from unittest.mock import patch

from app.queue.publisher import publish_processing_job
from app.queue.pubsub_publisher import publish_pubsub_job


def test_publish_processing_job_uses_celery_backend():
    with patch("app.queue.publisher.settings.queue_backend", "celery"), patch(
        "app.queue.publisher.publish_celery_job"
    ) as publish_celery:
        publish_processing_job(42)
    publish_celery.assert_called_once_with(42)


def test_publish_processing_job_uses_pubsub_backend():
    with patch("app.queue.publisher.settings.queue_backend", "pubsub"), patch(
        "app.queue.publisher.publish_pubsub_job"
    ) as publish_pubsub:
        publish_processing_job(84)
    publish_pubsub.assert_called_once_with(84)


def test_publish_pubsub_job_serializes_expected_event():
    client = types.SimpleNamespace()
    future = types.SimpleNamespace()
    future.result = lambda timeout=10: "ok"
    client.topic_path = lambda project, topic: f"projects/{project}/topics/{topic}"
    publish_calls = []

    def _publish(topic_path, payload):
        publish_calls.append((topic_path, payload))
        return future

    client.publish = _publish
    fake_pubsub_v1 = types.SimpleNamespace(PublisherClient=lambda: client)

    with patch(
        "app.queue.pubsub_publisher.settings.gcp_project_id",
        "proj",
    ), patch("app.queue.pubsub_publisher.settings.pubsub_topic_name", "topic"), patch.dict(
        "sys.modules",
        {"google.cloud.pubsub_v1": fake_pubsub_v1},
    ):
        publish_pubsub_job(101)

    assert len(publish_calls) == 1
    topic_path, payload_bytes = publish_calls[0]
    assert topic_path == "projects/proj/topics/topic"
    payload = json.loads(payload_bytes.decode("utf-8"))
    assert payload == {
        "event_type": "processing_job.created",
        "job_id": 101,
        "source": "cinetag-api",
    }

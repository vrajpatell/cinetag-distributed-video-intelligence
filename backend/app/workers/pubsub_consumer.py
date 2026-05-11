from __future__ import annotations

import json
import logging
import time

from app.bootstrap import ensure_preload

ensure_preload()

from app.core.config import settings  # noqa: E402
from app.db.models import ProcessingJob  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.observability.metrics import pubsub_messages_total  # noqa: E402
from app.queue.events import parse_processing_job_event  # noqa: E402
from app.workers.tasks import run_pipeline  # noqa: E402

logger = logging.getLogger(__name__)


def _handle_message(message) -> None:
    try:
        payload = json.loads(message.data.decode("utf-8"))
    except Exception:
        logger.warning("pubsub_malformed_json_acked")
        message.ack()
        pubsub_messages_total.labels(status="malformed_acked").inc()
        return

    try:
        job_id, meta = parse_processing_job_event(payload)
    except ValueError as exc:
        logger.warning("pubsub_invalid_event_acked error=%s", exc)
        message.ack()
        pubsub_messages_total.labels(status="invalid_acked").inc()
        return

    logger.info(
        "pubsub_message_received job_id=%s event_id=%s schema=%s",
        job_id,
        meta.get("event_id"),
        meta.get("schema_version"),
    )

    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            logger.warning("pubsub_unknown_job_acked job_id=%s", job_id)
            message.ack()
            pubsub_messages_total.labels(status="unknown_job_acked").inc()
            return
        if job.status in ("completed", "partially_completed"):
            logger.info(
                "pubsub_skip_already_finished job_id=%s status=%s",
                job_id,
                job.status,
            )
            message.ack()
            pubsub_messages_total.labels(status="skip_finished_acked").inc()
            return
        if job.status == "running":
            logger.info("pubsub_skip_running job_id=%s", job_id)
            message.ack()
            pubsub_messages_total.labels(status="skip_running_acked").inc()
            return
    finally:
        db.close()

    try:
        run_pipeline(job_id)
        message.ack()
        pubsub_messages_total.labels(status="acked").inc()
        logger.info("pubsub_pipeline_ok job_id=%s", job_id)
    except Exception:
        logger.exception("pubsub_pipeline_nack job_id=%s", job_id)
        message.nack()
        pubsub_messages_total.labels(status="nacked").inc()


def run_consumer() -> None:
    from google.cloud import pubsub_v1

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        settings.gcp_project_id,
        settings.pubsub_subscription_name,
    )
    flow_control = pubsub_v1.types.FlowControl(max_messages=2)
    future = subscriber.subscribe(subscription_path, callback=_handle_message, flow_control=flow_control)
    logger.info("pubsub_consumer_started subscription=%s", subscription_path)
    try:
        future.result()
    except KeyboardInterrupt:
        future.cancel()
    finally:
        subscriber.close()


if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level)
    while True:
        run_consumer()
        time.sleep(1)

from __future__ import annotations

import json
import logging
import time

from app.core.config import settings
from app.observability.metrics import pubsub_messages_total
from app.workers.tasks import run_pipeline

logger = logging.getLogger(__name__)


def _handle_message(message) -> None:
    try:
        payload = json.loads(message.data.decode("utf-8"))
        job_id = int(payload["job_id"])
        logger.info("pubsub_message_received job_id=%s", job_id)
        run_pipeline(job_id)
        message.ack()
        pubsub_messages_total.labels(status="acked").inc()
    except Exception:
        logger.exception("pubsub_message_failed")
        message.nack()
        pubsub_messages_total.labels(status="nacked").inc()


def run_consumer() -> None:
    from google.cloud import pubsub_v1

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        settings.gcp_project_id,
        settings.pubsub_subscription_name,
    )
    future = subscriber.subscribe(subscription_path, callback=_handle_message)
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

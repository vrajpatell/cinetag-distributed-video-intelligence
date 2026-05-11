"""Unit tests for Pub/Sub consumer message handling."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import sessionmaker

from app.db.models import ProcessingJob, VideoAsset
from app.db.session import Base
from app.queue.events import build_processing_job_event


def test_parse_event_roundtrip():
    ev = build_processing_job_event(7)
    from app.queue.events import parse_processing_job_event

    jid, _ = parse_processing_job_event(ev)
    assert jid == 7


def test_malformed_json_acks():
    from app.workers import pubsub_consumer

    msg = MagicMock()
    msg.data = b"not-json"
    pubsub_consumer._handle_message(msg)
    msg.ack.assert_called_once()
    msg.nack.assert_not_called()


def test_invalid_schema_acks():
    from app.workers import pubsub_consumer

    msg = MagicMock()
    msg.data = json.dumps({"job_id": 1}).encode()
    pubsub_consumer._handle_message(msg)
    msg.ack.assert_called_once()


def test_skip_completed_job_acks_without_pipeline(db_engine, monkeypatch):
    from app.workers import pubsub_consumer

    Base.metadata.create_all(bind=db_engine)
    S = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)
    s = S()
    v = VideoAsset(
        title="V",
        original_filename="v.mp4",
        storage_key="originals/v/v.mp4",
        status="published",
    )
    s.add(v)
    s.commit()
    s.refresh(v)
    job = ProcessingJob(video_id=v.id, status="completed", current_stage="completed")
    s.add(job)
    s.commit()
    s.refresh(job)
    s.close()

    monkeypatch.setattr(pubsub_consumer, "SessionLocal", S)

    msg = MagicMock()
    msg.data = json.dumps(build_processing_job_event(job.id)).encode()
    with patch.object(pubsub_consumer, "run_pipeline") as rp:
        pubsub_consumer._handle_message(msg)
    rp.assert_not_called()
    msg.ack.assert_called_once()

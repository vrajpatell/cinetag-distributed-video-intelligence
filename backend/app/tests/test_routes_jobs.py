"""Tests for the jobs control plane (list / get / retry)."""

from __future__ import annotations

from unittest.mock import patch

from app.api import routes_jobs
from app.db.models import ProcessingJob, VideoAsset


def _seed_failed_job(db) -> ProcessingJob:
    v = VideoAsset(
        title="Failed",
        original_filename="failed.mp4",
        storage_key="originals/f/failed.mp4",
        status="failed",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    j = ProcessingJob(
        video_id=v.id,
        status="failed",
        current_stage="frame_sampling",
        retry_count=1,
        error_message="ffprobe segfault",
    )
    db.add(j)
    db.commit()
    db.refresh(j)
    return j


def test_list_jobs_returns_paginated_payload(client):
    res = client.get("/api/jobs")
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "page" in body
    assert "total" in body
    assert isinstance(body["items"], list)


def test_get_job_returns_404_when_missing(client):
    res = client.get("/api/jobs/123456")
    assert res.status_code == 404


def test_retry_job_404_when_missing(client):
    res = client.post("/api/jobs/999999/retry")
    assert res.status_code == 404


def test_retry_job_increments_count_and_resets_status(client, db_session):
    job = _seed_failed_job(db_session)

    with patch.object(routes_jobs, "publish_processing_job") as delayed:
        res = client.post(f"/api/jobs/{job.id}/retry")

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "retried"
    assert body["job_id"] == job.id
    assert body["retry_count"] == 2
    delayed.assert_called_once_with(job.id)

    db_session.expire_all()
    refreshed = db_session.get(ProcessingJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "queued"
    assert refreshed.current_stage == "frame_sampling"
    assert refreshed.error_message is None
    assert refreshed.retry_count == 2
    assert refreshed.started_at is None
    assert refreshed.completed_at is None


def test_retry_job_returns_503_when_broker_offline(client, db_session):
    job = _seed_failed_job(db_session)

    with patch.object(
        routes_jobs,
        "publish_processing_job",
        side_effect=RuntimeError("redis broker offline"),
    ):
        res = client.post(f"/api/jobs/{job.id}/retry")

    assert res.status_code == 503
    assert "queue" in res.json()["detail"].lower()

    # The DB row was already reset before the broker call. The operator can
    # see the retry attempt; no duplicate job row was created.
    db_session.expire_all()
    refreshed = db_session.get(ProcessingJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "queued"
    assert refreshed.current_stage == "frame_sampling"
    assert refreshed.retry_count == 2
    assert refreshed.error_message is None

    jobs_for_video = (
        db_session.query(ProcessingJob).filter_by(video_id=job.video_id).count()
    )
    assert jobs_for_video == 1

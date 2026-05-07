from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.db.models import (
    EmbeddingRecord,
    FrameSample,
    GeneratedTag,
    ProcessingJob,
    ProcessingStageRun,
    SceneSegment,
    Transcript,
    VideoAsset,
)
from app.storage import get_object_store
from app.workers import tasks


def _bind_worker_to_test_db(monkeypatch, db_engine):
    session_local = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, future=True
    )
    monkeypatch.setattr(tasks, "SessionLocal", session_local)


def _seed_uploaded_video(db_session, storage_key: str = "originals/abc/video.mp4"):
    get_object_store().upload_bytes(storage_key, b"not-a-real-video", "video/mp4")
    video = VideoAsset(
        title="Pipeline Test",
        original_filename="video.mp4",
        storage_key=storage_key,
        status="uploaded",
        file_size_bytes=16,
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    job = ProcessingJob(video_id=video.id, status="queued", current_stage="queued")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return video, job


def test_run_pipeline_creates_analysis_outputs(monkeypatch, client, db_engine, db_session):
    _bind_worker_to_test_db(monkeypatch, db_engine)
    monkeypatch.setattr(tasks, "_ffprobe_metadata", lambda _path: {})
    monkeypatch.setattr(tasks, "_extract_frame_bytes", lambda _path, _ts: None)
    video, job = _seed_uploaded_video(db_session)

    result = tasks.run_pipeline(job.id)

    assert result == {"job_id": job.id, "status": "completed"}

    db_session.expire_all()
    refreshed_video = db_session.get(VideoAsset, video.id)
    refreshed_job = db_session.get(ProcessingJob, job.id)
    assert refreshed_video.status == "review_ready"
    assert refreshed_video.duration_seconds == 60.0
    assert refreshed_video.width == 1920
    assert refreshed_video.height == 1080
    assert refreshed_job.status == "completed"
    assert refreshed_job.current_stage == "completed"
    assert refreshed_job.started_at is not None
    assert refreshed_job.completed_at is not None

    assert db_session.query(FrameSample).filter_by(video_id=video.id).count() == 3
    assert db_session.query(SceneSegment).filter_by(video_id=video.id).count() == 4
    assert db_session.query(Transcript).filter_by(video_id=video.id).count() == 1
    assert db_session.query(GeneratedTag).filter_by(video_id=video.id).count() > 0
    assert db_session.query(EmbeddingRecord).filter_by(video_id=video.id).count() > 0
    assert (
        db_session.query(ProcessingStageRun).filter_by(job_id=job.id, status="completed").count()
        == len(tasks.PIPELINE_STAGES)
    )

    res = client.get(f"/api/videos/{video.id}")
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["processingStage"] == "completed"
    assert payload["tags"]
    assert payload["genres"]


def test_run_pipeline_marks_job_failed_when_stage_fails(
    monkeypatch, db_engine, db_session
):
    _bind_worker_to_test_db(monkeypatch, db_engine)
    video, job = _seed_uploaded_video(db_session, "originals/def/video.mp4")

    def boom(_db, _video, _ctx):
        raise RuntimeError("metadata unavailable")

    monkeypatch.setitem(tasks.STAGE_HANDLERS, "metadata_extraction", boom)

    try:
        tasks.run_pipeline(job.id)
    except RuntimeError as exc:
        assert "metadata unavailable" in str(exc)
    else:
        raise AssertionError("pipeline should re-raise stage failures")

    db_session.expire_all()
    refreshed_video = db_session.get(VideoAsset, video.id)
    refreshed_job = db_session.get(ProcessingJob, job.id)
    assert refreshed_video.status == "failed"
    assert refreshed_job.status == "failed"
    assert refreshed_job.current_stage == "metadata_extraction"
    assert "metadata unavailable" in refreshed_job.error_message

    failed_run = (
        db_session.query(ProcessingStageRun)
        .filter_by(job_id=job.id, stage_name="metadata_extraction")
        .first()
    )
    assert failed_run is not None
    assert failed_run.status == "failed"
    assert "metadata unavailable" in failed_run.error_message

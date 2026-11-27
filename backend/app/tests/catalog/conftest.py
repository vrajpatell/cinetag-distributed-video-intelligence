from datetime import datetime

import pytest

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


@pytest.fixture()
def catalog_db(db_session):
    db = db_session
    db.add_all(
        [
            VideoAsset(
                id=11,
                title="Coast_100%!",
                original_filename="coast.mp4",
                storage_key="private/coast.mp4",
                status="review_ready",
                summary="A walk along the estuary.",
                duration_seconds=12,
                width=1920,
                height=1080,
                frame_rate=25,
                bitrate=5000,
                codec="h264",
                file_size_bytes=4096,
                created_at=datetime(2024, 1, 1, 12),
            ),
            VideoAsset(
                id=12,
                title="Coast road",
                original_filename="road.mov",
                storage_key="private/road.mov",
                status="published",
                summary=" ",
                duration_seconds=8,
                width=720,
                height=1280,
                codec="h264",
                created_at=datetime(2024, 1, 2, 12),
            ),
            VideoAsset(
                id=13,
                title=None,
                original_filename="pending.mkv",
                storage_key="private/pending.mkv",
                status="upload_pending",
                created_at=datetime(2024, 1, 3, 12),
            ),
        ]
    )
    db.flush()
    db.add_all(
        [
            Transcript(
                video_id=11, text="The estuary\nopens into the sea.", language="en", confidence=0.95
            ),
            SceneSegment(
                id=20,
                video_id=11,
                start_time_seconds=7.125,
                end_time_seconds=12,
                summary="Boats & dunes",
            ),
            SceneSegment(
                id=21, video_id=11, start_time_seconds=0, end_time_seconds=7.125, summary="=Estuary"
            ),
            SceneSegment(
                id=22, video_id=12, start_time_seconds=5, end_time_seconds=3, summary=None
            ),
            FrameSample(
                video_id=11,
                timestamp_seconds=0,
                storage_key="private/frame.jpg",
                description="Blue water",
            ),
            GeneratedTag(
                id=31,
                video_id=11,
                tag_type="genre",
                tag_value="Travel",
                status="approved",
                source="manual",
                confidence=1,
                rationale="Human review",
            ),
            GeneratedTag(
                id=32,
                video_id=11,
                tag_type="mood",
                tag_value="Quiet",
                status="rejected",
                source="llm",
                confidence=0.35,
            ),
            GeneratedTag(
                id=33,
                video_id=12,
                tag_type="genre",
                tag_value="Travel",
                status="pending_review",
                source="llm",
                confidence=0.4,
            ),
            ProcessingJob(
                id=41, video_id=11, current_stage="completed", status="completed", retry_count=1
            ),
            ProcessingJob(
                id=42,
                video_id=12,
                current_stage="transcription",
                status="failed",
                error_message=None,
            ),
            EmbeddingRecord(
                video_id=11,
                entity_type="video",
                entity_id=11,
                embedding=[0.1, 0.2],
                embedding_model="unit-test-model",
                text="A walk along the estuary.",
                embedding_provider="mock",
                embedding_dimension=2,
            ),
        ]
    )
    db.flush()
    db.add_all(
        [
            ProcessingStageRun(
                job_id=41, stage_name="embedding", status="completed", duration_ms=250
            ),
            ProcessingStageRun(
                job_id=42,
                stage_name="transcription",
                status="failed",
                error_message="decoder failed",
            ),
        ]
    )
    db.commit()
    return db

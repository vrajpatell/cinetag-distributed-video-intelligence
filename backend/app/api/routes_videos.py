from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import (
    FrameSample,
    GeneratedTag,
    ProcessingJob,
    SceneSegment,
    Transcript,
    VideoAsset,
)
from app.db.session import get_db

router = APIRouter(prefix="/videos")


def _serialize_video(video: VideoAsset, db: Session) -> dict[str, Any]:
    tags = db.query(GeneratedTag).filter_by(video_id=video.id).all()
    job = (
        db.query(ProcessingJob)
        .filter_by(video_id=video.id)
        .order_by(ProcessingJob.id.desc())
        .first()
    )
    transcript = db.query(Transcript).filter_by(video_id=video.id).first()
    approved_or_pending = [t for t in tags if t.status in ("approved", "pending_review")]
    return {
        "id": video.id,
        "title": video.title,
        "description": transcript.text[:300] if transcript else None,
        "duration_seconds": video.duration_seconds,
        "status": video.status,
        "tags": [
            {
                "value": tag.tag_value,
                "type": tag.tag_type,
                "confidence": tag.confidence,
            }
            for tag in approved_or_pending
        ],
        "genres": sorted(
            {tag.tag_value for tag in approved_or_pending if tag.tag_type == "genre"}
        ),
        "moods": sorted(
            {tag.tag_value for tag in approved_or_pending if tag.tag_type == "mood"}
        ),
        "confidence": max(
            (tag.confidence or 0.0 for tag in approved_or_pending),
            default=None,
        ),
        "processingStage": job.current_stage if job else None,
        "width": video.width,
        "height": video.height,
        "codec": video.codec,
        "bitrate": video.bitrate,
        "frame_rate": video.frame_rate,
        "file_size_bytes": video.file_size_bytes,
        "created_at": video.created_at.isoformat() if video.created_at else None,
        "updated_at": video.updated_at.isoformat() if video.updated_at else None,
        "storage_key": video.storage_key,
    }


@router.get("")
def list_videos(db: Session = Depends(get_db)):
    return [_serialize_video(video, db) for video in db.query(VideoAsset).all()]


@router.get("/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(VideoAsset, video_id)
    if not video:
        raise HTTPException(404)
    return _serialize_video(video, db)


@router.get("/{video_id}/frames")
def frames(video_id: int, db: Session = Depends(get_db)):
    return db.query(FrameSample).filter_by(video_id=video_id).all()


@router.get("/{video_id}/scenes")
def scenes(video_id: int, db: Session = Depends(get_db)):
    return db.query(SceneSegment).filter_by(video_id=video_id).all()


@router.get("/{video_id}/transcript")
def transcript(video_id: int, db: Session = Depends(get_db)):
    return db.query(Transcript).filter_by(video_id=video_id).first()


@router.get("/{video_id}/tags")
def tags(video_id: int, db: Session = Depends(get_db)):
    return db.query(GeneratedTag).filter_by(video_id=video_id).all()

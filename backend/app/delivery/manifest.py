"""Build an editorial handoff from persisted metadata without accessing original media."""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GeneratedTag, SceneSegment, Transcript, VideoAsset
from app.delivery.schema import (
    Chapter,
    DeliveredTag,
    DeliveryManifest,
    DeliveryTranscript,
    MediaInfo,
    Notice,
)


def finite(value):
    return value if value is not None and math.isfinite(value) else None


def millis(seconds: float) -> int:
    return int((Decimal(str(seconds)) * 1000).to_integral_value(rounding=ROUND_HALF_UP))


def chapters_from_scenes(rows: list[SceneSegment], duration: float | None):
    chapters = []
    notices = []
    known_end = millis(duration) if duration and duration > 0 else None
    previous_end = 0
    for scene in rows:
        start = finite(scene.start_time_seconds)
        end = finite(scene.end_time_seconds)
        if start is None or end is None or start < 0 or end <= start:
            notices.append(
                Notice(
                    code="invalid_interval",
                    scene_id=scene.id,
                    message="Omitted a scene with invalid timestamps.",
                )
            )
            continue
        first, last = millis(start), millis(end)
        if known_end is not None and last > known_end:
            last = known_end
            notices.append(
                Notice(
                    code="past_duration",
                    scene_id=scene.id,
                    message="The scene extends beyond the recorded video duration.",
                )
            )
        if first < previous_end:
            first = previous_end
            notices.append(
                Notice(
                    code="overlap",
                    scene_id=scene.id,
                    message="Trimmed the overlapping start to the preceding chapter end.",
                )
            )
        if last <= first:
            notices.append(
                Notice(
                    code="empty_interval",
                    scene_id=scene.id,
                    message="Omitted a scene with no exportable interval.",
                )
            )
            continue
        title = " ".join((scene.summary or "").split()) or f"Scene {len(chapters) + 1}"
        chapters.append(Chapter(scene_id=scene.id, start_ms=first, end_ms=last, title=title))
        previous_end = last
    return chapters, notices


def load_manifest(db: Session, video_id: int) -> DeliveryManifest | None:
    asset = db.get(VideoAsset, video_id)
    if asset is None:
        return None
    media = MediaInfo(
        video_id=asset.id,
        title=asset.title,
        filename=asset.original_filename,
        status=asset.status,
        summary=asset.summary,
        duration_seconds=finite(asset.duration_seconds),
        width=asset.width,
        height=asset.height,
        codec=asset.codec,
        bitrate=asset.bitrate,
        frame_rate=finite(asset.frame_rate),
        file_size_bytes=asset.file_size_bytes,
    )
    scenes = db.scalars(
        select(SceneSegment)
        .where(SceneSegment.video_id == video_id)
        .order_by(SceneSegment.start_time_seconds, SceneSegment.id)
    ).all()
    chapters, notices = chapters_from_scenes(scenes, media.duration_seconds)
    row = db.scalar(select(Transcript).where(Transcript.video_id == video_id))
    transcript = None
    if row and row.text.strip():
        transcript = DeliveryTranscript(
            text=row.text, language=row.language, confidence=finite(row.confidence)
        )
    approved = db.scalars(
        select(GeneratedTag)
        .where(GeneratedTag.video_id == video_id, GeneratedTag.status == "approved")
        .order_by(GeneratedTag.tag_type, GeneratedTag.tag_value, GeneratedTag.id)
    )
    tags = [
        DeliveredTag(
            id=tag.id,
            type=tag.tag_type,
            value=tag.tag_value,
            source=tag.source,
            confidence=finite(tag.confidence),
            rationale=tag.rationale,
        )
        for tag in approved
    ]
    return DeliveryManifest(
        media=media, chapters=chapters, notices=notices, transcript=transcript, tags=tags
    )

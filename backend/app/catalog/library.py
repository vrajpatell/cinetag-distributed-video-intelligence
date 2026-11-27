"""Editorial catalog reports and their reusable row selections."""

from sqlalchemy import and_, exists, func, or_, select

from app.catalog.dataset import Column, Dataset, Preset
from app.catalog.schema import Kind
from app.db.models import (
    EmbeddingRecord,
    FrameSample,
    GeneratedTag,
    SceneSegment,
    Transcript,
    VideoAsset,
)


def blank(column):
    return or_(column.is_(None), func.trim(column) == "")


def asset_has(model, *conditions):
    return exists(select(model.id).where(model.video_id == VideoAsset.id, *conditions))


def finished_asset():
    return VideoAsset.status.in_(("review_ready", "published"))


ASSETS = Dataset(
    key="videos",
    label="Videos",
    description="Catalog records, technical metadata, and publication readiness.",
    model=VideoAsset,
    video_id=VideoAsset.id,
    columns=(
        Column(VideoAsset.id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Title"),
        Column(VideoAsset.status, "Status", groupable=True),
        Column(VideoAsset.original_filename, "Original filename"),
        Column(VideoAsset.summary, "Summary"),
        Column(VideoAsset.duration_seconds, "Duration", Kind.duration),
        Column(VideoAsset.width, "Width", Kind.integer),
        Column(VideoAsset.height, "Height", Kind.integer),
        Column(VideoAsset.frame_rate, "Frames per second", Kind.decimal),
        Column(VideoAsset.codec, "Codec", groupable=True),
        Column(VideoAsset.bitrate, "Bitrate (bps)", Kind.integer),
        Column(VideoAsset.file_size_bytes, "File size", Kind.size),
        Column(VideoAsset.created_at, "Uploaded", Kind.date),
        Column(VideoAsset.updated_at, "Last updated", Kind.date),
    ),
    defaults=("title", "status", "duration_seconds", "codec", "created_at"),
    search=(VideoAsset.title, VideoAsset.original_filename, VideoAsset.summary),
    presets=(
        Preset(
            "missing_summary",
            "Missing summary",
            "Processed videos without a catalog summary.",
            lambda: and_(finished_asset(), blank(VideoAsset.summary)),
            quality=True,
        ),
        Preset(
            "missing_duration",
            "Unknown duration",
            "Processed videos with an absent or nonpositive duration.",
            lambda: and_(
                finished_asset(),
                or_(VideoAsset.duration_seconds.is_(None), VideoAsset.duration_seconds <= 0),
            ),
            quality=True,
        ),
        Preset(
            "missing_transcript",
            "Missing transcript",
            "Processed videos without a nonempty transcript record.",
            lambda: and_(finished_asset(), ~asset_has(Transcript, ~blank(Transcript.text))),
            quality=True,
        ),
        Preset(
            "missing_scenes",
            "Missing scene boundaries",
            "Processed videos without any scene records.",
            lambda: and_(finished_asset(), ~asset_has(SceneSegment)),
            quality=True,
        ),
        Preset(
            "missing_embedding",
            "Missing embeddings",
            "Processed videos with no embedding records.",
            lambda: and_(finished_asset(), ~asset_has(EmbeddingRecord)),
            quality=True,
        ),
        Preset(
            "missing_frames",
            "Missing sampled frames",
            "Processed videos without sampled frame metadata.",
            lambda: and_(finished_asset(), ~asset_has(FrameSample)),
            quality=True,
        ),
        Preset(
            "ready_to_publish",
            "Ready to publish",
            "Review-ready videos with an approved tag and no pending tags.",
            lambda: and_(
                VideoAsset.status == "review_ready",
                asset_has(GeneratedTag, GeneratedTag.status == "approved"),
                ~asset_has(GeneratedTag, GeneratedTag.status == "pending_review"),
            ),
        ),
        Preset(
            "published_pending",
            "Published with pending tags",
            "Published assets that currently have tags awaiting a decision.",
            lambda: and_(
                VideoAsset.status == "published",
                asset_has(GeneratedTag, GeneratedTag.status == "pending_review"),
            ),
            quality=True,
        ),
        Preset(
            "portrait",
            "Portrait videos",
            "Assets whose recorded height exceeds their width.",
            lambda: and_(VideoAsset.width > 0, VideoAsset.height > VideoAsset.width),
        ),
    ),
)


TAGS = Dataset(
    key="tags",
    label="Tags",
    description="Review decisions, confidence scores, and tag provenance.",
    model=GeneratedTag,
    video_id=GeneratedTag.video_id,
    columns=(
        Column(GeneratedTag.id, "Tag ID", Kind.integer),
        Column(GeneratedTag.video_id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Video title"),
        Column(GeneratedTag.tag_type, "Type", groupable=True),
        Column(GeneratedTag.tag_value, "Tag", groupable=True),
        Column(GeneratedTag.confidence, "Confidence", Kind.confidence),
        Column(GeneratedTag.source, "Source", groupable=True),
        Column(GeneratedTag.status, "Decision", groupable=True),
        Column(GeneratedTag.rationale, "Rationale"),
        Column(GeneratedTag.created_at, "Created", Kind.date),
        Column(GeneratedTag.updated_at, "Updated", Kind.date),
    ),
    defaults=("tag_value", "title", "tag_type", "status", "confidence", "source"),
    search=(GeneratedTag.tag_value, GeneratedTag.rationale, VideoAsset.title),
    joins=((VideoAsset, VideoAsset.id == GeneratedTag.video_id),),
    presets=(
        Preset(
            "low_confidence",
            "Low-confidence suggestions",
            "Pending suggestions with confidence below 50 percent.",
            lambda: and_(GeneratedTag.status == "pending_review", GeneratedTag.confidence < 0.5),
        ),
        Preset(
            "unexplained",
            "Missing rationale",
            "Pending suggestions without a recorded rationale.",
            lambda: and_(GeneratedTag.status == "pending_review", blank(GeneratedTag.rationale)),
            quality=True,
        ),
        Preset(
            "invalid_confidence",
            "Invalid confidence",
            "Recorded scores outside the inclusive range zero to one.",
            lambda: or_(GeneratedTag.confidence < 0, GeneratedTag.confidence > 1),
            quality=True,
        ),
        Preset(
            "blank_tag",
            "Empty tag value",
            "Labels containing only whitespace or no text.",
            lambda: blank(GeneratedTag.tag_value),
            quality=True,
        ),
        Preset(
            "manual",
            "Manual decisions",
            "Tags attributed to a human editor.",
            lambda: GeneratedTag.source == "manual",
        ),
    ),
)


SCENES = Dataset(
    key="scenes",
    label="Scenes",
    description="Scene intervals and summaries across the library.",
    model=SceneSegment,
    video_id=SceneSegment.video_id,
    columns=(
        Column(SceneSegment.id, "Scene ID", Kind.integer),
        Column(SceneSegment.video_id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Video title"),
        Column(SceneSegment.start_time_seconds, "Starts at", Kind.duration),
        Column(SceneSegment.end_time_seconds, "Ends at", Kind.duration),
        Column(SceneSegment.summary, "Scene summary"),
        Column(SceneSegment.created_at, "Created", Kind.date),
    ),
    defaults=("title", "start_time_seconds", "end_time_seconds", "summary"),
    search=(VideoAsset.title, SceneSegment.summary),
    joins=((VideoAsset, VideoAsset.id == SceneSegment.video_id),),
    presets=(
        Preset(
            "invalid_interval",
            "Invalid interval",
            "Segments with a negative start or an end at or before the start.",
            lambda: or_(
                SceneSegment.start_time_seconds < 0,
                SceneSegment.end_time_seconds <= SceneSegment.start_time_seconds,
            ),
            quality=True,
        ),
        Preset(
            "past_duration",
            "Beyond video duration",
            "Scenes ending more than one frame-rounding allowance (0.1 s) beyond the recorded video duration.",
            lambda: and_(
                VideoAsset.duration_seconds > 0,
                SceneSegment.end_time_seconds > VideoAsset.duration_seconds + 0.1,
            ),
            quality=True,
        ),
        Preset(
            "unlabeled",
            "Missing description",
            "Scenes with no summary text.",
            lambda: blank(SceneSegment.summary),
            quality=True,
        ),
    ),
)


TRANSCRIPTS = Dataset(
    key="transcripts",
    label="Transcripts",
    description="Search spoken text, inspect languages, and find transcription gaps.",
    model=Transcript,
    video_id=Transcript.video_id,
    columns=(
        Column(Transcript.id, "Transcript ID", Kind.integer),
        Column(Transcript.video_id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Video title"),
        Column(Transcript.text, "Transcript"),
        Column(Transcript.language, "Language", groupable=True),
        Column(Transcript.confidence, "Confidence", Kind.confidence),
        Column(Transcript.created_at, "Created", Kind.date),
    ),
    defaults=("title", "language", "confidence", "text"),
    search=(VideoAsset.title, Transcript.text),
    joins=((VideoAsset, VideoAsset.id == Transcript.video_id),),
    presets=(
        Preset(
            "empty_text",
            "Empty transcript",
            "Transcript records with no speech text.",
            lambda: blank(Transcript.text),
            quality=True,
        ),
        Preset(
            "missing_language",
            "Missing language",
            "Transcript records without a language identifier.",
            lambda: blank(Transcript.language),
            quality=True,
        ),
        Preset(
            "mock_text",
            "Placeholder transcripts",
            "Rows containing the worker's explicit mock transcript prefix.",
            lambda: Transcript.text.startswith("Auto transcript placeholder for "),
            quality=True,
        ),
    ),
)


FRAMES = Dataset(
    key="frames",
    label="Frames",
    description="Inspect visual descriptions and the times at which frames were sampled.",
    model=FrameSample,
    video_id=FrameSample.video_id,
    columns=(
        Column(FrameSample.id, "Frame ID", Kind.integer),
        Column(FrameSample.video_id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Video title"),
        Column(FrameSample.timestamp_seconds, "Timestamp", Kind.duration),
        Column(FrameSample.description, "Description"),
        Column(FrameSample.created_at, "Created", Kind.date),
    ),
    defaults=("title", "timestamp_seconds", "description"),
    search=(VideoAsset.title, FrameSample.description),
    joins=((VideoAsset, VideoAsset.id == FrameSample.video_id),),
    presets=(
        Preset(
            "undescribed",
            "Missing visual description",
            "Sampled frames without a textual description.",
            lambda: blank(FrameSample.description),
            quality=True,
        ),
        Preset(
            "outside_video",
            "Out-of-range frame",
            "Frames with negative timestamps or timestamps past the recorded duration.",
            lambda: or_(
                FrameSample.timestamp_seconds < 0,
                and_(
                    VideoAsset.duration_seconds > 0,
                    FrameSample.timestamp_seconds > VideoAsset.duration_seconds + 0.1,
                ),
            ),
            quality=True,
        ),
    ),
)

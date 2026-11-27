"""Operational reports for pipeline runs and embedding inventories."""

from sqlalchemy import and_, or_

from app.catalog.dataset import Column, Dataset, Preset
from app.catalog.library import blank
from app.catalog.schema import Kind
from app.db.models import EmbeddingRecord, ProcessingJob, ProcessingStageRun, VideoAsset

JOBS = Dataset(
    key="jobs",
    label="Jobs",
    description="Compare processing outcomes, failure messages, and retry counts.",
    model=ProcessingJob,
    video_id=ProcessingJob.video_id,
    columns=(
        Column(ProcessingJob.id, "Job ID", Kind.integer),
        Column(ProcessingJob.video_id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Video title"),
        Column(ProcessingJob.status, "Status", groupable=True),
        Column(ProcessingJob.current_stage, "Current stage", groupable=True),
        Column(ProcessingJob.retry_count, "Retries", Kind.integer, groupable=True),
        Column(ProcessingJob.error_message, "Error message"),
        Column(ProcessingJob.started_at, "Started", Kind.date),
        Column(ProcessingJob.completed_at, "Completed", Kind.date),
        Column(ProcessingJob.created_at, "Queued", Kind.date),
        Column(ProcessingJob.updated_at, "Updated", Kind.date),
    ),
    defaults=("title", "status", "current_stage", "retry_count", "created_at"),
    search=(VideoAsset.title, ProcessingJob.current_stage, ProcessingJob.error_message),
    joins=((VideoAsset, VideoAsset.id == ProcessingJob.video_id),),
    presets=(
        Preset(
            "retried",
            "Retried jobs",
            "Jobs with at least one recorded retry.",
            lambda: ProcessingJob.retry_count > 0,
        ),
        Preset(
            "degraded",
            "Partial completion",
            "Jobs that produced partial results.",
            lambda: ProcessingJob.status == "partially_completed",
        ),
        Preset(
            "unexplained_failure",
            "Failures without a message",
            "Failed jobs without an error message for the operator.",
            lambda: and_(ProcessingJob.status == "failed", blank(ProcessingJob.error_message)),
            quality=True,
        ),
        Preset(
            "reversed_times",
            "Reversed job times",
            "The completion timestamp precedes the start timestamp.",
            lambda: ProcessingJob.completed_at < ProcessingJob.started_at,
            quality=True,
        ),
    ),
)


STAGES = Dataset(
    key="stages",
    label="Stage runs",
    description="Inspect timings, stage failures, and gaps in pipeline telemetry.",
    model=ProcessingStageRun,
    video_id=ProcessingJob.video_id,
    columns=(
        Column(ProcessingStageRun.id, "Run ID", Kind.integer),
        Column(ProcessingStageRun.job_id, "Job ID", Kind.integer),
        Column(ProcessingJob.video_id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Video title"),
        Column(ProcessingStageRun.stage_name, "Stage", groupable=True),
        Column(ProcessingStageRun.status, "Status", groupable=True),
        Column(ProcessingStageRun.duration_ms, "Elapsed time", Kind.elapsed),
        Column(ProcessingStageRun.error_message, "Error message"),
        Column(ProcessingStageRun.started_at, "Started", Kind.date),
        Column(ProcessingStageRun.completed_at, "Completed", Kind.date),
    ),
    defaults=("title", "job_id", "stage_name", "status", "duration_ms"),
    search=(VideoAsset.title, ProcessingStageRun.stage_name, ProcessingStageRun.error_message),
    joins=(
        (ProcessingJob, ProcessingJob.id == ProcessingStageRun.job_id),
        (VideoAsset, VideoAsset.id == ProcessingJob.video_id),
    ),
    presets=(
        Preset(
            "failed",
            "Failed stages",
            "Stages that recorded a failed outcome.",
            lambda: ProcessingStageRun.status == "failed",
        ),
        Preset(
            "missing_timing",
            "Missing elapsed time",
            "Completed stages with no recorded duration.",
            lambda: and_(
                ProcessingStageRun.status == "completed", ProcessingStageRun.duration_ms.is_(None)
            ),
            quality=True,
        ),
        Preset(
            "invalid_timing",
            "Invalid stage timing",
            "Negative elapsed time or a completion timestamp before the start.",
            lambda: or_(
                ProcessingStageRun.duration_ms < 0,
                ProcessingStageRun.completed_at < ProcessingStageRun.started_at,
            ),
            quality=True,
        ),
    ),
)


EMBEDDINGS = Dataset(
    key="embeddings",
    label="Embeddings",
    description="Inventory embedding providers, models, and stored dimensions.",
    model=EmbeddingRecord,
    video_id=EmbeddingRecord.video_id,
    columns=(
        Column(EmbeddingRecord.id, "Record ID", Kind.integer),
        Column(EmbeddingRecord.video_id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Video title"),
        Column(EmbeddingRecord.entity_type, "Entity type", groupable=True),
        Column(EmbeddingRecord.entity_id, "Entity ID", Kind.integer),
        Column(EmbeddingRecord.embedding_model, "Model", groupable=True),
        Column(EmbeddingRecord.embedding_provider, "Provider", groupable=True),
        Column(EmbeddingRecord.embedding_dimension, "Dimensions", Kind.integer, groupable=True),
        Column(EmbeddingRecord.created_at, "Created", Kind.date),
    ),
    defaults=(
        "title",
        "entity_type",
        "embedding_model",
        "embedding_provider",
        "embedding_dimension",
    ),
    search=(VideoAsset.title, EmbeddingRecord.embedding_model, EmbeddingRecord.embedding_provider),
    joins=((VideoAsset, VideoAsset.id == EmbeddingRecord.video_id),),
    presets=(
        Preset(
            "missing_provenance",
            "Missing model provenance",
            "The provider or model name was not recorded.",
            lambda: or_(
                blank(EmbeddingRecord.embedding_provider), blank(EmbeddingRecord.embedding_model)
            ),
            quality=True,
        ),
        Preset(
            "unknown_dimension",
            "Unknown vector dimensions",
            "The dimension is missing or nonpositive.",
            lambda: or_(
                EmbeddingRecord.embedding_dimension.is_(None),
                EmbeddingRecord.embedding_dimension <= 0,
            ),
            quality=True,
        ),
    ),
)

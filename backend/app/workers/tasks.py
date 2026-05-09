from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from celery import Celery
from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.db.session import SessionLocal
from app.ml.providers import embed_text, generate_tag_bundle, transcribe_audio
from app.ml.tag_schema import TagBundle
from app.observability.metrics import (
    jobs_failed_total,
    jobs_total,
    stage_duration,
    tags_generated,
    videos_processed,
)
from app.storage import get_object_store

celery = Celery(
    __name__,
    broker=settings.effective_broker_url,
    backend=settings.effective_result_backend,
)
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
logger = logging.getLogger(__name__)

PIPELINE_STAGES: tuple[str, ...] = (
    "metadata_extraction",
    "frame_sampling",
    "scene_segmentation",
    "transcription",
    "llm_tagging",
    "embedding",
    "review_ready",
    "completed",
)

# 1x1 black JPEG used as a safe placeholder when ffmpeg is unavailable. This
# keeps the API contract (image/jpeg) honest -- a downstream image renderer
# can decode it instead of getting bytes that look like text.
_PLACEHOLDER_JPEG_BYTES: bytes = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
    "0709090808"
    "0a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c283728"
    "2c303134341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d18321f1c"
    "1f323232323232323232323232323232323232323232323232323232323232323232"
    "323232323232323232323232323232323232ffc00011080001000103012200021101"
    "031101ffc4001f0000010501010101010100000000000000000102030405060708090"
    "a0bffc400b5100002010303020403050504040000017d01020300041105122131410"
    "613516107227114328191a1082342b1c11552d1f02433627282090a161718191a252"
    "62728292a3435363738393a434445464748494a535455565758595a636465666768"
    "696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a"
    "8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e"
    "5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffc4001f0100030101010101010101010100"
    "000000000001020304050607008090a0bffc400b5110002010204040304070504040"
    "0010277000102031104052131061241510761711322328108144291a1b1c109233352"
    "f0156272d10a162434e125f11718191a262728292a35363738393a4344454647484"
    "94a535455565758595a636465666768696a737475767778797a82838485868788898"
    "a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c"
    "8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c"
    "03010002110311003f00fbd040000000000ffd9"
)


@dataclass
class PipelineContext:
    original_path: str | None
    temp_dir: str
    # Each entry is (stage_name, reason). Stages that recover via local
    # placeholders/fallbacks call ctx.note_degraded(...) so the worker can
    # mark the job partially_completed instead of fully completed.
    degraded: list[tuple[str, str]] | None = None

    def note_degraded(self, stage: str, reason: str) -> None:
        if self.degraded is None:
            self.degraded = []
        self.degraded.append((stage, reason))


StageFn = Callable[[Session, VideoAsset, PipelineContext], None]
STAGE_INDEX = {stage: index for index, stage in enumerate(PIPELINE_STAGES)}


def _now() -> datetime:
    return datetime.utcnow()


def _delete_existing_outputs(db: Session, video_id: int) -> None:
    """Make reruns idempotent by replacing generated pipeline outputs."""
    for model in (FrameSample, SceneSegment, Transcript, GeneratedTag, EmbeddingRecord):
        db.query(model).filter(model.video_id == video_id).delete(
            synchronize_session=False
        )


def _delete_outputs_from_stage(db: Session, video_id: int, start_stage: str) -> None:
    """Clear only artifacts that could be stale when resuming a failed stage."""
    start = STAGE_INDEX.get(start_stage, 0)
    if start <= STAGE_INDEX["frame_sampling"]:
        db.query(FrameSample).filter_by(video_id=video_id).delete(
            synchronize_session=False
        )
    if start <= STAGE_INDEX["scene_segmentation"]:
        db.query(SceneSegment).filter_by(video_id=video_id).delete(
            synchronize_session=False
        )
    if start <= STAGE_INDEX["transcription"]:
        db.query(Transcript).filter_by(video_id=video_id).delete(
            synchronize_session=False
        )
    if start <= STAGE_INDEX["llm_tagging"]:
        db.query(GeneratedTag).filter_by(video_id=video_id).delete(
            synchronize_session=False
        )
    if start <= STAGE_INDEX["embedding"]:
        db.query(EmbeddingRecord).filter_by(video_id=video_id).delete(
            synchronize_session=False
        )


def _run_stage(
    db: Session,
    job_id: int,
    stage_name: str,
    stage_fn: StageFn,
    ctx: PipelineContext,
) -> None:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise ValueError(f"Processing job {job_id} not found")
    video = db.get(VideoAsset, job.video_id)
    if video is None:
        raise ValueError(f"Video asset {job.video_id} not found")

    job.status = "running"
    job.current_stage = stage_name
    if job.started_at is None:
        job.started_at = _now()
    if stage_name not in ("review_ready", "completed"):
        video.status = "processing"

    run = ProcessingStageRun(
        job_id=job.id,
        stage_name=stage_name,
        status="running",
        started_at=_now(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    started = time.perf_counter()
    logger.info("worker_stage_started job_id=%s stage=%s", job_id, stage_name)
    try:
        stage_fn(db, video, ctx)
    except Exception as exc:
        db.rollback()
        run = db.get(ProcessingStageRun, run.id)
        job = db.get(ProcessingJob, job_id)
        video = db.get(VideoAsset, video.id)
        if run is not None:
            run.status = "failed"
            run.completed_at = _now()
            run.duration_ms = int((time.perf_counter() - started) * 1000)
            run.error_message = str(exc)
        if job is not None:
            job.status = "failed"
            job.current_stage = stage_name
            job.error_message = str(exc)
            job.completed_at = _now()
        if video is not None:
            video.status = "failed"
        db.commit()
        logger.exception("worker_stage_failed job_id=%s stage=%s", job_id, stage_name)
        stage_duration.labels(stage_name).observe(time.perf_counter() - started)
        raise

    run.status = "completed"
    run.completed_at = _now()
    run.duration_ms = int((time.perf_counter() - started) * 1000)
    db.commit()
    logger.info(
        "worker_stage_completed job_id=%s stage=%s duration_ms=%s",
        job_id,
        stage_name,
        run.duration_ms,
    )
    stage_duration.labels(stage_name).observe(time.perf_counter() - started)


def _local_original_path(video: VideoAsset) -> str | None:
    store = get_object_store()
    if not hasattr(store, "_path"):
        return None
    try:
        path = store._path(video.storage_key)  # LocalStore helper.
    except Exception:
        return None
    return str(path) if Path(path).exists() else None


def _safe_suffix(storage_key: str) -> str:
    suffix = Path(storage_key).suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix or "") else ".bin"


def _materialize_original(video: VideoAsset, temp_dir: str) -> str | None:
    """Return a local file path for LocalStore or download remote storage once."""
    local_path = _local_original_path(video)
    if local_path:
        return local_path

    destination = Path(temp_dir) / f"original_{video.id}{_safe_suffix(video.storage_key)}"
    if destination.exists():
        return str(destination)

    store = get_object_store()
    try:
        store.download_file(video.storage_key, str(destination))
    except Exception:
        logger.exception(
            "original_materialization_failed video_id=%s storage_key=%s",
            video.id,
            video.storage_key,
        )
        return None
    return str(destination) if destination.exists() else None


def _ffprobe_metadata(local_path: str) -> dict[str, Any]:
    if shutil.which("ffprobe") is None:
        return {}
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                local_path,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return json.loads(proc.stdout or "{}")
    except Exception:
        logger.exception("ffprobe_metadata_failed path=%s", local_path)
        return {}


def _first_video_stream(payload: dict[str, Any]) -> dict[str, Any]:
    for stream in payload.get("streams") or []:
        if stream.get("codec_type") == "video":
            return stream
    return {}


def _fraction_to_float(raw: str | None) -> float | None:
    if not raw:
        return None
    if "/" not in raw:
        try:
            return float(raw)
        except ValueError:
            return None
    num, den = raw.split("/", 1)
    try:
        denominator = float(den)
        return float(num) / denominator if denominator else None
    except ValueError:
        return None


def _metadata_extraction(db: Session, video: VideoAsset, ctx: PipelineContext) -> None:
    payload = _ffprobe_metadata(ctx.original_path) if ctx.original_path else {}
    if not payload:
        if settings.media_strict:
            raise RuntimeError(
                "metadata_extraction failed: ffprobe unavailable or video unreadable"
            )
        ctx.note_degraded(
            "metadata_extraction",
            "ffprobe unavailable; using deterministic placeholder metadata",
        )
    stream = _first_video_stream(payload)
    fmt = payload.get("format") or {}

    if fmt.get("duration"):
        video.duration_seconds = float(fmt["duration"])
    elif video.duration_seconds is None:
        video.duration_seconds = 60.0

    if stream.get("width"):
        video.width = int(stream["width"])
    elif video.width is None:
        video.width = 1920

    if stream.get("height"):
        video.height = int(stream["height"])
    elif video.height is None:
        video.height = 1080

    video.codec = stream.get("codec_name") or video.codec or "unknown"
    if fmt.get("bit_rate"):
        video.bitrate = int(fmt["bit_rate"])
    elif video.bitrate is None:
        video.bitrate = 0

    video.frame_rate = (
        _fraction_to_float(stream.get("avg_frame_rate"))
        or _fraction_to_float(stream.get("r_frame_rate"))
        or video.frame_rate
        or 30.0
    )
    db.add(video)


def _sample_timestamps(duration_seconds: float | None, count: int = 3) -> list[float]:
    duration = max(float(duration_seconds or 60.0), 1.0)
    if count <= 1:
        return [min(duration / 2, duration)]
    return [round(duration * (i + 1) / (count + 1), 3) for i in range(count)]


def _extract_frame_bytes(local_path: str, timestamp: float) -> bytes | None:
    if shutil.which("ffmpeg") is None:
        return None
    with tempfile.TemporaryDirectory(prefix="cinetag-frame-") as tmp:
        out = Path(tmp) / "frame.jpg"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(timestamp),
                    "-i",
                    local_path,
                    "-frames:v",
                    "1",
                    "-q:v",
                    "3",
                    str(out),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
            return out.read_bytes() if out.exists() else None
        except Exception:
            logger.exception("ffmpeg_frame_extract_failed path=%s ts=%s", local_path, timestamp)
            return None


def _detect_scene_timestamps(local_path: str) -> list[float]:
    """Use ffmpeg scene-change detection; return boundary timestamps."""
    if shutil.which("ffmpeg") is None:
        return []
    threshold = settings.scene_detection_threshold
    try:
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-i",
                local_path,
                "-filter:v",
                f"select='gt(scene,{threshold})',showinfo",
                "-f",
                "null",
                "-",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception:
        logger.exception("ffmpeg_scene_detection_failed path=%s", local_path)
        return []

    timestamps: list[float] = []
    try:
        if proc.stderr is not None:
            for line in proc.stderr:
                match = re.search(r"pts_time:([0-9]+(?:\.[0-9]+)?)", line)
                if match is None:
                    continue
                try:
                    timestamps.append(round(float(match.group(1)), 3))
                except ValueError:
                    continue
                if len(timestamps) >= 200:
                    # Scene stage only needs coarse boundaries; cap growth to
                    # avoid noisy videos consuming unbounded memory.
                    break
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
    except Exception:
        proc.kill()
        logger.exception("ffmpeg_scene_detection_stream_failed path=%s", local_path)
        return []
    return sorted(set(timestamps))[:20]


def _extract_audio(local_path: str, temp_dir: str, video_id: int) -> str | None:
    if shutil.which("ffmpeg") is None:
        return None
    out = Path(temp_dir) / f"audio_{video_id}.mp3"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                local_path,
                "-vn",
                "-acodec",
                "libmp3lame",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(out),
            ],
            check=True,
            capture_output=True,
            timeout=90,
        )
        return str(out) if out.exists() else None
    except Exception:
        logger.exception("ffmpeg_audio_extract_failed path=%s", local_path)
        return None


def _frame_sampling(db: Session, video: VideoAsset, ctx: PipelineContext) -> None:
    store = get_object_store()
    used_placeholder = False
    for index, ts in enumerate(_sample_timestamps(video.duration_seconds), start=1):
        key = f"frames/{video.id}/frame_{index:03d}.jpg"
        extracted = (
            _extract_frame_bytes(ctx.original_path, ts)
            if ctx.original_path
            else None
        )
        if extracted is None:
            used_placeholder = True
            data = _PLACEHOLDER_JPEG_BYTES
            description = (
                f"Placeholder 1x1 frame at {ts:.2f}s (ffmpeg unavailable)"
            )
        else:
            data = extracted
            description = f"Representative frame sampled at {ts:.2f}s"
        store.upload_bytes(key, data, content_type="image/jpeg")
        db.add(
            FrameSample(
                video_id=video.id,
                timestamp_seconds=ts,
                storage_key=key,
                description=description,
            )
        )

    if used_placeholder:
        if settings.media_strict:
            raise RuntimeError(
                "frame_sampling failed: ffmpeg unavailable or frames unreadable"
            )
        ctx.note_degraded(
            "frame_sampling",
            "ffmpeg unavailable; persisted 1x1 placeholder JPEGs",
        )


def _scene_segmentation(db: Session, video: VideoAsset, ctx: PipelineContext) -> None:
    timestamps = _detect_scene_timestamps(ctx.original_path) if ctx.original_path else []
    if not timestamps:
        timestamps = _sample_timestamps(video.duration_seconds)
    duration = float(video.duration_seconds or 60.0)
    boundaries = sorted({0.0, *[ts for ts in timestamps if 0 < ts < duration], duration})
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        db.add(
            SceneSegment(
                video_id=video.id,
                start_time_seconds=round(start, 3),
                end_time_seconds=round(max(end, start + 0.001), 3),
                summary=f"Scene {index}: automatically segmented content window.",
            )
        )


def _transcription(db: Session, video: VideoAsset, ctx: PipelineContext) -> None:
    title = video.title or video.original_filename
    fallback = (
        f"Auto transcript placeholder for {title}. "
        "Speech-to-text provider is configured for mock local processing."
    )
    audio_path = (
        _extract_audio(ctx.original_path, ctx.temp_dir, video.id)
        if ctx.original_path
        else None
    )
    if audio_path is None and settings.media_strict:
        raise RuntimeError(
            "transcription failed: could not extract audio for STT"
        )

    text, confidence, provider = transcribe_audio(audio_path, fallback)
    if provider == "mock" and settings.transcription_provider != "mock":
        ctx.note_degraded(
            "transcription",
            f"transcription provider {settings.transcription_provider} fell back to mock",
        )
    db.add(Transcript(video_id=video.id, text=text, language="en", confidence=confidence))
    store = get_object_store()
    store.upload_bytes(
        f"transcripts/{video.id}/transcript.txt",
        text.encode(),
        content_type="text/plain",
    )
    logger.info("transcription_completed video_id=%s provider=%s", video.id, provider)


def _tag_values(bundle: TagBundle) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for tag_type, values in (
        ("genre", bundle.genres),
        ("mood", bundle.moods),
        ("theme", bundle.themes),
        ("object", bundle.objects),
        ("scene", bundle.settings),
        ("moderation", bundle.content_warnings),
        ("entity", bundle.marketing_keywords + bundle.search_keywords),
    ):
        for value in values:
            out.append((tag_type, value, "llm"))
    out.append(("language", bundle.age_suitability.suggested_rating, "metadata"))
    return out


def _llm_tagging(db: Session, video: VideoAsset, ctx: PipelineContext) -> None:
    transcript = db.query(Transcript).filter_by(video_id=video.id).first()
    frames = db.query(FrameSample).filter_by(video_id=video.id).all()
    scenes = db.query(SceneSegment).filter_by(video_id=video.id).all()
    prompt = "\n".join(
        [
            f"title={video.title}",
            f"metadata={video.duration_seconds}s {video.width}x{video.height} {video.codec}",
            f"transcript={(transcript.text if transcript else '')[:1000]}",
            f"frames={len(frames)} scenes={len(scenes)}",
        ]
    )
    bundle = generate_tag_bundle(prompt)
    video.title = video.title or video.original_filename
    video.summary = bundle.summary
    rationale = bundle.summary

    generated = 0
    for tag_type, tag_value, source in _tag_values(bundle):
        db.add(
            GeneratedTag(
                video_id=video.id,
                tag_type=tag_type,
                tag_value=tag_value,
                confidence=bundle.confidence,
                source=source,
                status="pending_review",
                rationale=rationale,
            )
        )
        generated += 1
    tags_generated.inc(generated)


def _embedding(db: Session, video: VideoAsset, ctx: PipelineContext) -> None:
    def _build_embedding_payload(text: str) -> dict[str, Any]:
        values = embed_text(text)
        if not values:
            raise RuntimeError("embedding stage produced an empty vector")
        dimension = len(values)
        vector = values if dimension == settings.embedding_vector_dimension else None
        return {
            "embedding": values,
            "embedding_vector": vector,
            "embedding_dimension": dimension,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.openai_embedding_model
            if settings.embedding_provider == "openai"
            else "mock-embedding",
        }

    transcript = db.query(Transcript).filter_by(video_id=video.id).first()
    if transcript is not None:
        payload = _build_embedding_payload(transcript.text)
        db.add(
            EmbeddingRecord(
                video_id=video.id,
                entity_type="transcript",
                entity_id=transcript.id or video.id,
                text=transcript.text,
                **payload,
            )
        )

    for tag in db.query(GeneratedTag).filter_by(video_id=video.id).all():
        text = f"{tag.tag_type}: {tag.tag_value}. {tag.rationale or ''}".strip()
        payload = _build_embedding_payload(text)
        db.add(
            EmbeddingRecord(
                video_id=video.id,
                entity_type="tag",
                entity_id=tag.id or 0,
                text=text,
                **payload,
            )
        )

    for scene in db.query(SceneSegment).filter_by(video_id=video.id).all():
        text = scene.summary or f"Scene from {scene.start_time_seconds} to {scene.end_time_seconds}"
        payload = _build_embedding_payload(text)
        db.add(
            EmbeddingRecord(
                video_id=video.id,
                entity_type="scene",
                entity_id=scene.id or 0,
                text=text,
                **payload,
            )
        )


def _review_ready(db: Session, video: VideoAsset, ctx: PipelineContext) -> None:
    video.status = "review_ready"
    for tag in db.query(GeneratedTag).filter_by(video_id=video.id).all():
        if not tag.status:
            tag.status = "pending_review"
    db.add(video)


def _completed(db: Session, video: VideoAsset, ctx: PipelineContext) -> None:
    # The asset remains review_ready until humans approve/publish tags; the job
    # itself is complete and discoverable via pending-review search results.
    video.status = "review_ready"
    db.add(video)


STAGE_HANDLERS: dict[str, StageFn] = {
    "metadata_extraction": _metadata_extraction,
    "frame_sampling": _frame_sampling,
    "scene_segmentation": _scene_segmentation,
    "transcription": _transcription,
    "llm_tagging": _llm_tagging,
    "embedding": _embedding,
    "review_ready": _review_ready,
    "completed": _completed,
}


@celery.task(name="run_pipeline")
def run_pipeline(job_id: int):
    jobs_total.inc()
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            raise ValueError(f"Processing job {job_id} not found")
        video = db.get(VideoAsset, job.video_id)
        if video is None:
            raise ValueError(f"Video asset {job.video_id} not found")

        start_stage = (
            job.current_stage
            if job.retry_count and job.current_stage in STAGE_INDEX
            else "metadata_extraction"
        )
        start_index = STAGE_INDEX[start_stage]
        if start_index == 0:
            _delete_existing_outputs(db, video.id)
        else:
            _delete_outputs_from_stage(db, video.id, start_stage)

        job.status = "running"
        job.current_stage = start_stage
        job.error_message = None
        job.started_at = job.started_at or _now()
        job.completed_at = None
        video.status = "processing"
        db.commit()

        with tempfile.TemporaryDirectory(prefix=f"cinetag-job-{job_id}-") as temp_dir:
            ctx = PipelineContext(
                original_path=_materialize_original(video, temp_dir),
                temp_dir=temp_dir,
            )
            if ctx.original_path is None:
                if settings.media_strict:
                    raise RuntimeError(
                        "could not materialize original media object for processing"
                    )
                ctx.note_degraded(
                    "metadata_extraction",
                    "could not download original; running pipeline with placeholders",
                )
            for stage in PIPELINE_STAGES[start_index:]:
                _run_stage(db, job_id, stage, STAGE_HANDLERS[stage], ctx)

        job = db.get(ProcessingJob, job_id)
        if job is None:
            raise ValueError(f"Processing job {job_id} disappeared")
        degraded = ctx.degraded or []
        if degraded:
            job.status = "partially_completed"
            job.error_message = "; ".join(f"{stage}: {reason}" for stage, reason in degraded)
        else:
            job.status = "completed"
        job.current_stage = "completed"
        job.completed_at = _now()
        db.commit()
        videos_processed.inc()
        return {
            "job_id": job_id,
            "status": job.status,
            "degraded_stages": [stage for stage, _ in degraded],
        }
    except Exception as exc:
        logger.exception("pipeline_failed job_id=%s", job_id)
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = _now()
            video = db.get(VideoAsset, job.video_id)
            if video is not None:
                video.status = "failed"
        db.commit()
        jobs_failed_total.inc()
        raise
    finally:
        db.close()

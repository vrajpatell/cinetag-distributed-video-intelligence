from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import EmbeddingRecord, GeneratedTag, VideoAsset
from app.db.session import get_db
from app.ml.providers import embed_text
from app.observability.metrics import (
    semantic_search_fallback_total,
    semantic_search_latency_seconds,
    semantic_search_total,
)

router = APIRouter(prefix="/search")
logger = logging.getLogger(__name__)


class Query(BaseModel):
    query: str
    tag_type: str | None = None
    status: str | None = None
    duration_min: float | None = None
    duration_max: float | None = None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _apply_pgvector_query(db: Session, q: Query, target: list[float]) -> dict[int, dict[str, Any]]:
    best: dict[int, dict[str, Any]] = {}
    distance_expr = EmbeddingRecord.embedding_vector.cosine_distance(target)
    query = (
        db.query(EmbeddingRecord, VideoAsset, distance_expr.label("distance"))
        .join(VideoAsset, VideoAsset.id == EmbeddingRecord.video_id)
        .filter(
            and_(
                EmbeddingRecord.embedding_vector.isnot(None),
                EmbeddingRecord.embedding_dimension == len(target),
            )
        )
    )
    if q.status:
        query = query.filter(VideoAsset.status == q.status)
    if q.duration_min is not None:
        query = query.filter(
            (VideoAsset.duration_seconds.isnot(None)) & (VideoAsset.duration_seconds >= q.duration_min)
        )
    if q.duration_max is not None:
        query = query.filter(
            (VideoAsset.duration_seconds.isnot(None)) & (VideoAsset.duration_seconds <= q.duration_max)
        )

    for rec, _video, distance in query.order_by(distance_expr.asc()).limit(500).all():
        score = 1.0 - float(distance or 1.0)
        cur = best.get(rec.video_id)
        if cur is None or score > cur["score"]:
            best[rec.video_id] = {
                "score": score,
                "entity_type": rec.entity_type,
                "snippet": rec.text,
            }
    return best


def _apply_python_scan(db: Session, q: Query, target: list[float], target_len: int) -> dict[int, dict[str, Any]]:
    best: dict[int, dict[str, Any]] = {}
    base = db.query(EmbeddingRecord, VideoAsset).join(
        VideoAsset, VideoAsset.id == EmbeddingRecord.video_id
    )
    if q.status:
        base = base.filter(VideoAsset.status == q.status)
    if q.duration_min is not None:
        base = base.filter(
            (VideoAsset.duration_seconds.isnot(None)) & (VideoAsset.duration_seconds >= q.duration_min)
        )
    if q.duration_max is not None:
        base = base.filter(
            (VideoAsset.duration_seconds.isnot(None)) & (VideoAsset.duration_seconds <= q.duration_max)
        )
    for rec, _video in base.all():
        if not rec.embedding or len(rec.embedding) != target_len:
            continue
        score = _cosine(target, rec.embedding)
        cur = best.get(rec.video_id)
        if cur is None or score > cur["score"]:
            best[rec.video_id] = {
                "score": float(score),
                "entity_type": rec.entity_type,
                "snippet": rec.text,
            }
    return best


@router.post("/semantic")
def semantic(q: Query, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    started = time.perf_counter()
    target = embed_text(q.query)
    target_len = len(target)
    if target_len == 0:
        semantic_search_total.labels(backend="none", status="error").inc()
        return []

    best: dict[int, dict[str, Any]] = {}
    backend_mode = settings.semantic_search_backend
    cfg_dim = settings.embedding_vector_dimension
    dim_matches_cfg = target_len == cfg_dim
    metric_backend = "python"

    def _observe(status: str) -> None:
        semantic_search_total.labels(backend=metric_backend, status=status).inc()
        semantic_search_latency_seconds.labels(backend=metric_backend).observe(
            time.perf_counter() - started
        )

    if backend_mode == "python":
        best = _apply_python_scan(db, q, target, target_len)
        metric_backend = "python"
    elif backend_mode == "pgvector":
        if not dim_matches_cfg:
            semantic_search_total.labels(backend="pgvector", status="dim_mismatch").inc()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"SEMANTIC_SEARCH_BACKEND=pgvector requires embedding dimension {cfg_dim}, "
                    f"got {target_len} from the active embedding provider"
                ),
            )
        if not settings.pgvector_enabled:
            semantic_search_total.labels(backend="pgvector", status="disabled").inc()
            raise HTTPException(
                status_code=503,
                detail="pgvector is disabled (PGVECTOR_ENABLED=false)",
            )
        try:
            best = _apply_pgvector_query(db, q, target)
            metric_backend = "pgvector"
        except Exception as exc:
            logger.exception("semantic_search_pgvector_failed")
            semantic_search_total.labels(backend="pgvector", status="error").inc()
            raise HTTPException(status_code=503, detail="pgvector query failed") from exc
    else:  # auto
        skip_pg = (not settings.pgvector_enabled) or (not dim_matches_cfg)
        if skip_pg:
            if not dim_matches_cfg:
                logger.info(
                    "semantic_search_skipping_pgvector dimension_mismatch target_dim=%s config_dim=%s",
                    target_len,
                    cfg_dim,
                )
            best = _apply_python_scan(db, q, target, target_len)
            metric_backend = "python"
        else:
            used_python_fallback = False
            try:
                best = _apply_pgvector_query(db, q, target)
                metric_backend = "pgvector"
            except Exception:
                logger.warning("semantic_search_pgvector_fallback_to_python", exc_info=True)
                semantic_search_fallback_total.inc()
                best = _apply_python_scan(db, q, target, target_len)
                metric_backend = "python"
                used_python_fallback = True
            if not best and not used_python_fallback:
                logger.info("semantic_search_pgvector_empty_fallback_python")
                semantic_search_fallback_total.inc()
                best = _apply_python_scan(db, q, target, target_len)
                metric_backend = "python"

    if not best:
        _observe("empty")
        return []

    video_ids = list(best.keys())
    videos = {v.id: v for v in db.query(VideoAsset).filter(VideoAsset.id.in_(video_ids)).all()}
    tags_by_video: dict[int, list[GeneratedTag]] = defaultdict(list)
    for t in db.query(GeneratedTag).filter(GeneratedTag.video_id.in_(video_ids)).all():
        tags_by_video[t.video_id].append(t)

    results: list[dict[str, Any]] = []
    for video_id, info in best.items():
        v = videos.get(video_id)
        if v is None:
            continue
        tags = tags_by_video.get(video_id, [])
        approved = [t for t in tags if t.status in ("approved", "pending_review")]

        genres = sorted({t.tag_value for t in approved if t.tag_type == "genre"})
        moods = sorted({t.tag_value for t in approved if t.tag_type == "mood"})
        matched_tags = [
            {"value": t.tag_value, "type": t.tag_type}
            for t in sorted(approved, key=lambda x: (x.confidence or 0.0), reverse=True)[:6]
        ]

        results.append(
            {
                "video_id": v.id,
                "title": v.title,
                "score": info["score"],
                "explanation": f"Matched {info['entity_type']}",
                "duration_seconds": v.duration_seconds,
                "status": v.status,
                "genres": genres,
                "moods": moods,
                "matched_tags": matched_tags,
            }
        )

    if q.tag_type:
        results = [r for r in results if any(mt["type"] == q.tag_type for mt in r["matched_tags"])]
    if q.status:
        results = [r for r in results if r.get("status") == q.status]
    if q.duration_min is not None:
        results = [r for r in results if (r.get("duration_seconds") or 0) >= q.duration_min]
    if q.duration_max is not None:
        results = [r for r in results if (r.get("duration_seconds") or 0) <= q.duration_max]

    _observe("success")
    return sorted(results, key=lambda x: x["score"], reverse=True)[:20]

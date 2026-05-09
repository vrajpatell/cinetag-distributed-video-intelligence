from __future__ import annotations

from collections import defaultdict
from typing import Any
import logging
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

import math

from app.db.models import EmbeddingRecord, GeneratedTag, VideoAsset
from app.db.session import get_db
from app.ml.providers import embed_text
from app.observability.metrics import semantic_search_latency_seconds, semantic_search_total
from app.core.config import settings

router = APIRouter(prefix='/search')
logger = logging.getLogger(__name__)


class Query(BaseModel):
    query: str
    tag_type: str | None = None
    status: str | None = None
    duration_min: float | None = None
    duration_max: float | None = None


def _cosine(a: list[float], b: list[float]) -> float:
    """Length-normalized cosine similarity.

    Different providers emit different vector lengths (mock=16, OpenAI=1536+).
    We treat dim-mismatched records as non-matches rather than zeroing out
    the entire scoreboard, so a corpus mid-migration still returns the
    matches it has.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@router.post('/semantic')
def semantic(q: Query, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Embedding-similarity search across the catalog.

    Returns one entry per video (best matching embedding wins) with enough
    metadata to power the discovery UI's filters: title, status, duration,
    genres, moods, and matched_tags. Without those fields, the frontend's
    genre/mood filters would silently exclude every real result.
    """
    started = time.perf_counter()
    target = embed_text(q.query)
    target_len = len(target)
    if target_len == 0:
        semantic_search_total.labels(backend="none", status="error").inc()
        return []

    best: dict[int, dict[str, Any]] = {}
    search_backend = "python"
    use_pgvector = settings.pgvector_enabled and settings.semantic_search_backend in (
        "auto",
        "pgvector",
    )
    should_use_python_fallback = not use_pgvector
    if use_pgvector:
        try:
            distance_expr = EmbeddingRecord.embedding_vector.cosine_distance(target)
            query = (
                db.query(EmbeddingRecord, VideoAsset, distance_expr.label("distance"))
                .join(VideoAsset, VideoAsset.id == EmbeddingRecord.video_id)
                .filter(
                    and_(
                        EmbeddingRecord.embedding_vector.isnot(None),
                        EmbeddingRecord.embedding_dimension == target_len,
                    )
                )
            )
            if q.status:
                query = query.filter(VideoAsset.status == q.status)
            if q.duration_min is not None:
                query = query.filter((VideoAsset.duration_seconds.isnot(None)) & (VideoAsset.duration_seconds >= q.duration_min))
            if q.duration_max is not None:
                query = query.filter((VideoAsset.duration_seconds.isnot(None)) & (VideoAsset.duration_seconds <= q.duration_max))

            for rec, _video, distance in query.order_by(distance_expr.asc()).limit(500).all():
                score = 1.0 - float(distance or 1.0)
                cur = best.get(rec.video_id)
                if cur is None or score > cur["score"]:
                    best[rec.video_id] = {
                        "score": score,
                        "entity_type": rec.entity_type,
                        "snippet": rec.text,
                    }
            search_backend = "pgvector"
        except Exception:
            if settings.semantic_search_backend == "pgvector" and settings.app_env != "local":
                raise
            logger.warning("semantic_search_pgvector_fallback_to_python")
            should_use_python_fallback = True

    if should_use_python_fallback:
        for rec in db.query(EmbeddingRecord).all():
            if not rec.embedding or len(rec.embedding) != target_len:
                continue
            score = _cosine(target, rec.embedding)
            cur = best.get(rec.video_id)
            if cur is None or score > cur['score']:
                best[rec.video_id] = {
                    'score': float(score),
                    'entity_type': rec.entity_type,
                    'snippet': rec.text,
                }

    if not best:
        semantic_search_total.labels(backend=search_backend, status="empty").inc()
        semantic_search_latency_seconds.labels(backend=search_backend).observe(
            time.perf_counter() - started
        )
        return []

    # 2) Pull every relevant video and tag in two queries (avoid N+1).
    video_ids = list(best.keys())
    videos = {
        v.id: v
        for v in db.query(VideoAsset).filter(VideoAsset.id.in_(video_ids)).all()
    }
    tags_by_video: dict[int, list[GeneratedTag]] = defaultdict(list)
    for t in (
        db.query(GeneratedTag).filter(GeneratedTag.video_id.in_(video_ids)).all()
    ):
        tags_by_video[t.video_id].append(t)

    results: list[dict[str, Any]] = []
    for video_id, info in best.items():
        v = videos.get(video_id)
        if v is None:
            continue
        tags = tags_by_video.get(video_id, [])
        approved = [t for t in tags if t.status in ('approved', 'pending_review')]

        genres = sorted({t.tag_value for t in approved if t.tag_type == 'genre'})
        moods = sorted({t.tag_value for t in approved if t.tag_type == 'mood'})
        matched_tags = [
            {'value': t.tag_value, 'type': t.tag_type}
            for t in sorted(
                approved, key=lambda x: (x.confidence or 0.0), reverse=True
            )[:6]
        ]

        results.append(
            {
                'video_id': v.id,
                'title': v.title,
                'score': info['score'],
                'explanation': f"Matched {info['entity_type']}",
                'duration_seconds': v.duration_seconds,
                'status': v.status,
                'genres': genres,
                'moods': moods,
                'matched_tags': matched_tags,
            }
        )

    # 3) Apply backend-level filters from the query payload.
    if q.tag_type:
        results = [
            r
            for r in results
            if any(mt['type'] == q.tag_type for mt in r['matched_tags'])
        ]
    if q.status:
        results = [r for r in results if r.get('status') == q.status]
    if q.duration_min is not None:
        results = [
            r
            for r in results
            if (r.get('duration_seconds') or 0) >= q.duration_min
        ]
    if q.duration_max is not None:
        results = [
            r
            for r in results
            if (r.get('duration_seconds') or 0) <= q.duration_max
        ]

    semantic_search_total.labels(backend=search_backend, status="success").inc()
    semantic_search_latency_seconds.labels(backend=search_backend).observe(
        time.perf_counter() - started
    )
    return sorted(results, key=lambda x: x['score'], reverse=True)[:20]

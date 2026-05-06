from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import EmbeddingRecord, GeneratedTag, VideoAsset
from app.db.session import get_db
from app.ml.mock_embedding_client import MockEmbeddingClient

router = APIRouter(prefix='/search')


class Query(BaseModel):
    query: str
    tag_type: str | None = None
    status: str | None = None
    duration_min: float | None = None
    duration_max: float | None = None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


@router.post('/semantic')
def semantic(q: Query, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Embedding-similarity search across the catalog.

    Returns one entry per video (best matching embedding wins) with enough
    metadata to power the discovery UI's filters: title, status, duration,
    genres, moods, and matched_tags. Without those fields, the frontend's
    genre/mood filters would silently exclude every real result.
    """
    target = MockEmbeddingClient().embed(q.query)

    # 1) Score every embedding record, keeping only the best score per video.
    best: dict[int, dict[str, Any]] = {}
    for rec in db.query(EmbeddingRecord).all():
        score = _cosine(target, rec.embedding)
        cur = best.get(rec.video_id)
        if cur is None or score > cur['score']:
            best[rec.video_id] = {
                'score': float(score),
                'entity_type': rec.entity_type,
                'snippet': rec.text,
            }

    if not best:
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

    return sorted(results, key=lambda x: x['score'], reverse=True)[:20]

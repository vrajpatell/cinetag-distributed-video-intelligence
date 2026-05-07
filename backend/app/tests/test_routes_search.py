"""Semantic-search behaviour for the catalog endpoint.

The pipeline can store embeddings produced by any provider (mock today,
OpenAI in production), so search must use the same provider as the worker.
We also need to gracefully ignore records whose vector dimensions do not
match the query vector (e.g. a corpus that is mid-migration between
providers) instead of zero-scoring everything.
"""

from __future__ import annotations

from app.db.models import EmbeddingRecord, GeneratedTag, VideoAsset


def _seed_video_with_embedding(
    db, *, title: str, storage_key: str, embedding: list[float], snippet: str = "snippet"
) -> VideoAsset:
    v = VideoAsset(
        title=title,
        original_filename=f"{title}.mp4",
        storage_key=storage_key,
        status="review_ready",
        duration_seconds=60.0,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    db.add(
        EmbeddingRecord(
            video_id=v.id,
            entity_type="transcript",
            entity_id=1,
            embedding=embedding,
            text=snippet,
        )
    )
    db.add(
        GeneratedTag(
            video_id=v.id,
            tag_type="genre",
            tag_value="drama",
            confidence=0.9,
            source="llm",
            status="approved",
        )
    )
    db.commit()
    return v


def test_semantic_search_uses_shared_provider_and_returns_results(client, db_session):
    # Mock embeddings are 16-dim; if /search/semantic still embedded with
    # MockEmbeddingClient directly instead of the providers shim we'd never
    # detect a regression where the worker switches to OpenAI but search
    # does not. Here we just assert the route returns a result for an
    # embedding produced against the same provider as the search endpoint.
    from app.ml.providers import embed_text

    target = embed_text("a moody thriller")
    _seed_video_with_embedding(
        db_session,
        title="Thriller A",
        storage_key="originals/sa/thriller-a.mp4",
        embedding=target,
        snippet="moody thriller",
    )

    res = client.post("/api/search/semantic", json={"query": "a moody thriller"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body, "search should return at least one result"
    assert body[0]["title"] == "Thriller A"


def test_semantic_search_skips_dim_mismatched_records(client, db_session):
    # A record whose embedding was produced with a different provider must
    # not poison the scoreboard. We seed two videos: one with the same dim
    # as the query, one with a wildly different dim, and assert only the
    # matching-dim video is returned.
    from app.ml.providers import embed_text

    target = embed_text("space opera")
    _seed_video_with_embedding(
        db_session,
        title="Same dim",
        storage_key="originals/sd/same-dim.mp4",
        embedding=target,
    )
    _seed_video_with_embedding(
        db_session,
        title="Different dim",
        storage_key="originals/dd/diff-dim.mp4",
        embedding=[0.1] * (len(target) + 7),
    )

    res = client.post("/api/search/semantic", json={"query": "space opera"})
    assert res.status_code == 200
    titles = [r["title"] for r in res.json()]
    assert "Same dim" in titles
    assert "Different dim" not in titles

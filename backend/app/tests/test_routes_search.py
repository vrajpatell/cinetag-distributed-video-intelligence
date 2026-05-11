"""Semantic-search behaviour for the catalog endpoint.

The pipeline can store embeddings produced by any provider (mock today,
OpenAI in production), so search must use the same provider as the worker.
We also need to gracefully ignore records whose vector dimensions do not
match the query vector (e.g. a corpus that is mid-migration between
providers) instead of zero-scoring everything.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from app.db.models import EmbeddingRecord, GeneratedTag, VideoAsset
from app.api.routes_search import Query, semantic


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
            embedding_vector=embedding if len(embedding) == 1536 else None,
            embedding_dimension=len(embedding),
            embedding_provider="mock",
            embedding_model="mock-embedding",
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


def test_semantic_search_filters_still_work(client, db_session):
    from app.ml.providers import embed_text

    target = embed_text("crime noir")
    v = _seed_video_with_embedding(
        db_session,
        title="Noir A",
        storage_key="originals/noir/a.mp4",
        embedding=target,
        snippet="dark noir",
    )
    v.status = "published"
    v.duration_seconds = 90.0
    db_session.commit()

    res = client.post(
        "/api/search/semantic",
        json={
            "query": "crime noir",
            "tag_type": "genre",
            "status": "published",
            "duration_min": 60,
            "duration_max": 100,
        },
    )
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "Noir A"


def test_semantic_search_python_fallback_when_pgvector_disabled(client, db_session, monkeypatch):
    from app.core.config import get_settings
    from app.ml.providers import embed_text

    monkeypatch.setenv("SEMANTIC_SEARCH_BACKEND", "python")
    get_settings.cache_clear()
    target = embed_text("mystery")
    _seed_video_with_embedding(
        db_session,
        title="Mystery A",
        storage_key="originals/mystery/a.mp4",
        embedding=target,
    )

    res = client.post("/api/search/semantic", json={"query": "mystery"})
    assert res.status_code == 200
    assert res.json()


def test_semantic_search_pgvector_forced_rejects_dimension_mismatch(client, db_session, monkeypatch):
    from app.core.config import get_settings
    from app.ml.providers import embed_text

    monkeypatch.setenv("SEMANTIC_SEARCH_BACKEND", "pgvector")
    get_settings.cache_clear()
    target = embed_text("any")
    assert len(target) != 1536
    _seed_video_with_embedding(
        db_session,
        title="X",
        storage_key="originals/x/x.mp4",
        embedding=target,
    )
    res = client.post("/api/search/semantic", json={"query": "any"})
    assert res.status_code == 400


def test_semantic_search_pgvector_mode_does_not_use_full_scan(monkeypatch):
    from app.api import routes_search

    @dataclass
    class _Rec:
        video_id: int
        entity_type: str
        text: str

    @dataclass
    class _Video:
        id: int
        title: str
        status: str
        duration_seconds: float

    class _PgVectorField:
        def cosine_distance(self, _target):
            return self

        def isnot(self, _value):
            return True

        def asc(self):
            return self

        def label(self, _name):
            return self

    class _FakeQuery:
        def __init__(self, rows):
            self._rows = rows

        def join(self, *_args, **_kwargs):
            return self

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            return self._rows

    class _FakeSession:
        def __init__(self):
            self.full_scan_called = False

        def query(self, *args):
            if len(args) == 3:
                rec = _Rec(video_id=1, entity_type="transcript", text="snippet")
                video = _Video(
                    id=1,
                    title="Vector Film",
                    status="review_ready",
                    duration_seconds=80.0,
                )
                return _FakeQuery([(rec, video, 0.1)])
            if len(args) == 1 and args[0] is EmbeddingRecord:
                self.full_scan_called = True
                return _FakeQuery([])
            if len(args) == 1 and args[0] is VideoAsset:
                return _FakeQuery(
                    [
                        _Video(
                            id=1,
                            title="Vector Film",
                            status="review_ready",
                            duration_seconds=80.0,
                        )
                    ]
                )
            if len(args) == 1 and args[0] is GeneratedTag:
                return _FakeQuery([])
            raise AssertionError("Unexpected query signature")

    monkeypatch.setattr(routes_search, "embed_text", lambda _text: [0.1] * 1536)
    monkeypatch.setattr(
        routes_search,
        "settings",
        SimpleNamespace(
            semantic_search_backend="pgvector",
            pgvector_enabled=True,
            app_env="local",
            embedding_vector_dimension=1536,
        ),
    )
    monkeypatch.setattr(routes_search.EmbeddingRecord, "embedding_vector", _PgVectorField())

    fake_db = _FakeSession()
    result = semantic(Query(query="vector"), db=fake_db)
    assert result
    assert result[0]["title"] == "Vector Film"
    assert fake_db.full_scan_called is False

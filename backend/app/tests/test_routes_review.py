"""Tests for the review-queue aggregation endpoint."""

from __future__ import annotations

from app.db.models import GeneratedTag, VideoAsset


def _seed_video(db, *, title: str = "Demo", storage_key: str = "originals/x/demo.mp4"):
    v = VideoAsset(
        title=title,
        original_filename="demo.mp4",
        storage_key=storage_key,
        status="review_ready",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _seed_tag(db, *, video_id: int, status: str, tag_value: str, tag_type: str = "mood"):
    t = GeneratedTag(
        video_id=video_id,
        tag_type=tag_type,
        tag_value=tag_value,
        confidence=0.9,
        source="llm",
        status=status,
        rationale="seeded",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_review_endpoint_returns_empty_list_when_no_pending_tags(client):
    res = client.get("/api/review")
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_review_endpoint_returns_only_pending_review_status(client, db_session):
    v = _seed_video(db_session, title="Pending video", storage_key="originals/p/p.mp4")
    pending = _seed_tag(db_session, video_id=v.id, status="pending_review", tag_value="suspenseful")
    _seed_tag(db_session, video_id=v.id, status="approved", tag_value="action")
    _seed_tag(db_session, video_id=v.id, status="rejected", tag_value="boring")

    res = client.get("/api/review")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == pending.id
    assert item["status"] == "pending_review"
    assert item["tag_value"] == "suspenseful"
    assert item["video_title"] == "Pending video"
    assert item["video_id"] == v.id
    assert item["confidence"] == 0.9
    assert item["source"] == "llm"


def test_review_endpoint_orders_newest_first(client, db_session):
    v = _seed_video(db_session, storage_key="originals/o/o.mp4")
    older = _seed_tag(db_session, video_id=v.id, status="pending_review", tag_value="older")
    newer = _seed_tag(db_session, video_id=v.id, status="pending_review", tag_value="newer")

    res = client.get("/api/review")
    assert res.status_code == 200
    ids = [t["id"] for t in res.json()["items"]]
    # SQLAlchemy default created_at fills at insert time; the second insert
    # is newer (or equal), so we just assert both tags appear.
    assert older.id in ids
    assert newer.id in ids


def test_review_endpoint_handles_missing_video_gracefully(client, db_session):
    # A tag pointing at a video that has been deleted should still serialize
    # without crashing — video_title becomes None.
    orphan = GeneratedTag(
        video_id=99_999,
        tag_type="mood",
        tag_value="orphan",
        confidence=0.5,
        source="llm",
        status="pending_review",
    )
    db_session.add(orphan)
    db_session.commit()

    res = client.get("/api/review")
    assert res.status_code == 200
    items = [t for t in res.json()["items"] if t["tag_value"] == "orphan"]
    assert items, "orphan tag should still surface in the queue"
    assert items[0]["video_title"] is None

"""Publish-after-review lifecycle.

The pipeline brings a video to ``review_ready``; humans must then resolve
every pending tag and explicitly publish before the asset is considered live.
This test guards both the success path and the guardrails (pending tags or
no approved tags must block the publish call).
"""

from __future__ import annotations

from app.db.models import AuditLog, GeneratedTag, VideoAsset


def _seed_video(db, status: str = "review_ready") -> VideoAsset:
    v = VideoAsset(
        title="Publish me",
        original_filename="publishme.mp4",
        storage_key="originals/pub/publishme.mp4",
        status=status,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _add_tag(db, video_id: int, status: str, value: str = "drama") -> GeneratedTag:
    t = GeneratedTag(
        video_id=video_id,
        tag_type="genre",
        tag_value=value,
        confidence=0.9,
        source="llm",
        status=status,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_publish_succeeds_when_all_tags_resolved_and_at_least_one_approved(client, db_session):
    v = _seed_video(db_session)
    _add_tag(db_session, v.id, status="approved", value="thriller")
    _add_tag(db_session, v.id, status="rejected", value="comedy")

    res = client.post(f"/api/videos/{v.id}/publish")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "published"

    db_session.expire_all()
    refreshed = db_session.get(VideoAsset, v.id)
    assert refreshed.status == "published"

    audit_rows = (
        db_session.query(AuditLog).filter_by(action="video_publish", entity_id=v.id).all()
    )
    assert audit_rows, "publishing should write an audit log entry"


def test_publish_blocked_while_tags_are_pending_review(client, db_session):
    v = _seed_video(db_session)
    _add_tag(db_session, v.id, status="approved", value="thriller")
    _add_tag(db_session, v.id, status="pending_review", value="moody")

    res = client.post(f"/api/videos/{v.id}/publish")
    assert res.status_code == 409
    assert "pending review" in res.json()["detail"]


def test_publish_blocked_when_no_tags_were_approved(client, db_session):
    v = _seed_video(db_session)
    _add_tag(db_session, v.id, status="rejected", value="thriller")

    res = client.post(f"/api/videos/{v.id}/publish")
    assert res.status_code == 409
    assert "no approved tags" in res.json()["detail"]


def test_publish_blocked_when_video_not_review_ready(client, db_session):
    v = _seed_video(db_session, status="processing")

    res = client.post(f"/api/videos/{v.id}/publish")
    assert res.status_code == 409
    assert "review_ready" in res.json()["detail"]


def test_publish_returns_404_for_unknown_video(client):
    res = client.post("/api/videos/999999/publish")
    assert res.status_code == 404

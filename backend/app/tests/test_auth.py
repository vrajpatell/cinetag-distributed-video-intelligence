from __future__ import annotations

from app.core.config import get_settings
from app.db.models import GeneratedTag, VideoAsset


def test_upload_rejects_without_key_when_auth_enabled(client, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "admintest")
    get_settings.cache_clear()
    res = client.post(
        "/api/uploads/init",
        json={
            "filename": "a.mp4",
            "content_type": "video/mp4",
            "size_bytes": 100,
        },
    )
    assert res.status_code == 401


def test_upload_accepts_admin_key_when_auth_enabled(client, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "admintest")
    get_settings.cache_clear()
    res = client.post(
        "/api/uploads/init",
        json={
            "filename": "a.mp4",
            "content_type": "video/mp4",
            "size_bytes": 100,
        },
        headers={"X-API-Key": "admintest"},
    )
    assert res.status_code == 200


def test_reviewer_can_patch_tag_when_auth_enabled(client, db_session, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("REVIEWER_API_KEY", "revtest")
    get_settings.cache_clear()
    v = VideoAsset(
        title="T",
        original_filename="t.mp4",
        storage_key="originals/t/t.mp4",
        status="review_ready",
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    t = GeneratedTag(
        video_id=v.id,
        tag_type="genre",
        tag_value="drama",
        confidence=0.9,
        source="llm",
        status="pending_review",
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)

    res = client.patch(
        f"/api/tags/{t.id}",
        json={"status": "approved"},
        headers={"X-API-Key": "revtest"},
    )
    assert res.status_code == 200


def test_reviewer_cannot_upload_when_auth_enabled(client, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("REVIEWER_API_KEY", "revtest")
    monkeypatch.setenv("ADMIN_API_KEY", "admintest")
    get_settings.cache_clear()
    res = client.post(
        "/api/uploads/init",
        json={
            "filename": "a.mp4",
            "content_type": "video/mp4",
            "size_bytes": 100,
        },
        headers={"X-API-Key": "revtest"},
    )
    assert res.status_code == 401

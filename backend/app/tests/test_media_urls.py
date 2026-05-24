"""Media URL fields on video list/detail responses."""

from __future__ import annotations

from pathlib import Path

from app.db.models import FrameSample, VideoAsset


def _seed_video(db, *, storage_key: str = "originals/abc/clip.mp4") -> VideoAsset:
    v = VideoAsset(
        title="Preview test",
        original_filename="clip.mp4",
        storage_key=storage_key,
        status="review_ready",
        duration_seconds=30.0,
        file_size_bytes=4096,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def test_list_videos_includes_poster_and_preview_fields(client, db_session):
    v = _seed_video(db_session)
    store_path = Path(db_session.bind.url.database if hasattr(db_session.bind, "url") else "")
    _ = store_path  # silence lint in minimal envs

    from app.storage.local_store import LocalStore

    store = LocalStore()
    frame_key = f"frames/{v.id}/frame_001.jpg"
    p: Path = store._resolve_safe(frame_key)  # noqa: SLF001
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xd8\xff\xd9")

    preview_key = f"previews/{v.id}/preview.mp4"
    pp: Path = store._resolve_safe(preview_key)  # noqa: SLF001
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_bytes(b"fake-mp4")

    orig_key = v.storage_key
    op: Path = store._resolve_safe(orig_key)  # noqa: SLF001
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_bytes(b"fake-video")

    db_session.add(
        FrameSample(
            video_id=v.id,
            timestamp_seconds=1.0,
            storage_key=frame_key,
            description="test frame",
        )
    )
    db_session.commit()

    res = client.get("/api/videos")
    assert res.status_code == 200
    item = next(i for i in res.json()["items"] if i["id"] == v.id)
    assert item["poster_url"] is not None
    assert item["thumbnail_urls"]
    assert item["preview_url"] is not None
    assert item["has_preview"] is True


def test_preview_endpoint_returns_signed_local_url(client, db_session):
    v = _seed_video(db_session)
    from app.storage.local_store import LocalStore

    store = LocalStore()
    preview_key = f"previews/{v.id}/preview.mp4"
    pp: Path = store._resolve_safe(preview_key)  # noqa: SLF001
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_bytes(b"fake-mp4")

    res = client.get(f"/api/videos/{v.id}/preview")
    assert res.status_code == 200
    body = res.json()
    assert body["preview_url"]
    assert body["expires_in_seconds"] > 0

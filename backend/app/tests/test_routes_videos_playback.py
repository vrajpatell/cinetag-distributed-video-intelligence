"""Playback endpoint behaviour.

Covers the ``/api/videos/{id}/playback`` and local-dev ``/stream`` paths.
The fixtures (see ``conftest.py``) configure ``STORAGE_BACKEND=minio`` which
falls through to ``LocalStore`` for ``get_object_store()``. We patch
``settings.storage_backend`` directly to exercise the GCS branch without
needing real GCS credentials.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.api import routes_videos
from app.core.config import settings
from app.db.models import FrameSample, VideoAsset
from app.storage.local_store import LocalStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_video(
    db,
    *,
    status: str = "review_ready",
    storage_key: str = "originals/abc/clip.mp4",
    duration: float | None = 12.5,
    size_bytes: int | None = 4096,
) -> VideoAsset:
    v = VideoAsset(
        title="Playable clip",
        original_filename="clip.mp4",
        storage_key=storage_key,
        status=status,
        duration_seconds=duration,
        file_size_bytes=size_bytes,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _write_local_object(storage_key: str, data: bytes) -> Path:
    """Write bytes into the configured LocalStore so object_exists is True."""
    store = LocalStore()
    p: Path = store._resolve_safe(storage_key)  # noqa: SLF001
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


# ---------------------------------------------------------------------------
# /playback
# ---------------------------------------------------------------------------


def test_playback_returns_404_for_unknown_video(client):
    res = client.get("/api/videos/999999/playback")
    assert res.status_code == 404


def test_playback_409_when_video_status_is_upload_pending(client, db_session):
    v = _seed_video(db_session, status="upload_pending")
    res = client.get(f"/api/videos/{v.id}/playback")
    assert res.status_code == 409
    assert "not playable" in res.json()["detail"]


def test_playback_409_when_storage_object_missing(client, db_session):
    # Status is fine, but no file backs the storage_key on disk.
    v = _seed_video(db_session, storage_key="originals/missing/clip.mp4")
    res = client.get(f"/api/videos/{v.id}/playback")
    assert res.status_code == 409
    assert "not present" in res.json()["detail"].lower()


def test_playback_local_returns_stream_url_and_metadata(client, db_session):
    v = _seed_video(db_session, storage_key="originals/ok/clip.mp4")
    _write_local_object(v.storage_key, b"\x00" * 256)

    res = client.get(f"/api/videos/{v.id}/playback")
    assert res.status_code == 200, res.text
    body = res.json()

    # Local dev points at our streaming endpoint, not at a signed GCS URL.
    assert body["url"].endswith(f"/api/videos/{v.id}/stream")
    assert body["content_type"] == "video/mp4"
    assert body["expires_in_seconds"] == 60 * 60
    assert body["duration_seconds"] == 12.5
    assert body["file_size_bytes"] == 4096
    assert body["poster_url"] is None  # no FrameSample seeded


def test_playback_local_returns_poster_url_when_frame_exists(client, db_session):
    v = _seed_video(db_session, storage_key="originals/ok/poster-test.mp4")
    _write_local_object(v.storage_key, b"\x00" * 64)
    frame = FrameSample(
        video_id=v.id,
        timestamp_seconds=2.0,
        storage_key="frames/ok/frame-0001.jpg",
    )
    db_session.add(frame)
    db_session.commit()
    db_session.refresh(frame)

    res = client.get(f"/api/videos/{v.id}/playback")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["poster_url"]
    assert body["poster_url"].endswith(f"/api/videos/frames/{frame.id}/image")


def test_playback_gcs_returns_signed_url(client, db_session):
    v = _seed_video(db_session, storage_key="originals/gcs/clip.mp4")
    _write_local_object(v.storage_key, b"\x00" * 32)  # for object_exists

    fake_url = "https://storage.googleapis.com/bucket/originals/gcs/clip.mp4?X-Goog-Signature=abc"

    class _FakeStore:
        def object_exists(self, key: str) -> bool:
            return True

        def generate_signed_url(self, key: str, *, expiration_seconds: int, method: str) -> str:
            assert method == "GET"
            assert expiration_seconds == 60 * 60
            return fake_url

    with patch.object(settings, "storage_backend", "gcs"), patch.object(
        routes_videos, "get_object_store", lambda: _FakeStore()
    ):
        res = client.get(f"/api/videos/{v.id}/playback")

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["url"] == fake_url


# ---------------------------------------------------------------------------
# /stream  (local dev only)
# ---------------------------------------------------------------------------


def test_stream_returns_full_file_when_no_range_header(client, db_session):
    payload = b"hello-world" * 50
    v = _seed_video(db_session, storage_key="originals/ok/stream-full.mp4")
    _write_local_object(v.storage_key, payload)

    res = client.get(f"/api/videos/{v.id}/stream")
    assert res.status_code == 200
    assert res.content == payload
    assert res.headers["accept-ranges"] == "bytes"
    assert int(res.headers["content-length"]) == len(payload)


def test_stream_honors_byte_range_header(client, db_session):
    payload = bytes(range(256))
    v = _seed_video(db_session, storage_key="originals/ok/stream-range.mp4")
    _write_local_object(v.storage_key, payload)

    res = client.get(
        f"/api/videos/{v.id}/stream",
        headers={"Range": "bytes=10-19"},
    )
    assert res.status_code == 206
    assert res.content == payload[10:20]
    assert res.headers["content-range"] == f"bytes 10-19/{len(payload)}"
    assert int(res.headers["content-length"]) == 10


def test_stream_returns_416_for_unsatisfiable_range(client, db_session):
    payload = b"x" * 50
    v = _seed_video(db_session, storage_key="originals/ok/stream-416.mp4")
    _write_local_object(v.storage_key, payload)

    res = client.get(
        f"/api/videos/{v.id}/stream",
        headers={"Range": "bytes=500-600"},
    )
    assert res.status_code == 416
    assert res.headers["content-range"] == f"bytes */{len(payload)}"


def test_stream_disabled_when_gcs_backend_is_active(client, db_session):
    v = _seed_video(db_session, storage_key="originals/gcs/stream.mp4")
    with patch.object(settings, "storage_backend", "gcs"):
        res = client.get(f"/api/videos/{v.id}/stream")
    assert res.status_code == 400
    assert "disabled" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Range header parsing (unit-level)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "header,size,expected",
    [
        ("bytes=0-99", 1000, (0, 99)),
        ("bytes=900-", 1000, (900, 999)),
        ("bytes=-100", 1000, (900, 999)),
        ("bytes=0-9999", 1000, (0, 999)),  # clamped to end
        ("", 1000, None),
        ("bytes=", 1000, None),
        ("bytes=abc-def", 1000, None),
        ("bytes=500-100", 1000, None),  # end < start
        ("bytes=2000-", 1000, None),    # start past EOF
    ],
)
def test_parse_range_header_cases(header, size, expected):
    assert routes_videos._parse_range_header(header, size) == expected

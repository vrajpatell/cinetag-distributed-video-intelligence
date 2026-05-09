"""Behavioural tests for the signed-upload control plane.

These tests verify the bug fixes called out in the field report:

* repeated calls with the same filename must not collide on storage_key
* the response shape always includes a fresh upload_url and unique key
* invalid content types and oversized payloads return clean 4xx errors

The test suite uses an in-memory SQLite (see ``conftest.py``) and the
``LocalStore`` filesystem backend, so no GCS credentials are required.
"""

from __future__ import annotations

from unittest.mock import patch

from app.api import routes_upload


def _payload(**overrides):
    base = {
        "filename": "test.mp4",
        "content_type": "video/mp4",
        "size_bytes": 1024,
        "title": "Test asset",
    }
    base.update(overrides)
    return base


def test_init_upload_returns_expected_shape(client):
    res = client.post("/api/uploads/init", json=_payload())
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) >= {
        "video_id",
        "storage_key",
        "upload_url",
        "upload_method",
        "required_headers",
        "expires_in_seconds",
    }
    assert body["upload_method"] == "PUT"
    assert body["required_headers"] == {"Content-Type": "video/mp4"}
    assert body["expires_in_seconds"] == 15 * 60
    assert body["upload_url"].endswith(body["storage_key"]) or body["upload_url"].startswith(
        "http"
    )


def test_init_upload_twice_with_same_filename_does_not_collide(client):
    first = client.post("/api/uploads/init", json=_payload(filename="test.mp4"))
    second = client.post("/api/uploads/init", json=_payload(filename="test.mp4"))

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    a = first.json()
    b = second.json()
    assert a["video_id"] != b["video_id"]
    assert a["storage_key"] != b["storage_key"]
    assert a["storage_key"].startswith("originals/")
    assert b["storage_key"].startswith("originals/")
    assert a["storage_key"].endswith("/test.mp4")
    assert b["storage_key"].endswith("/test.mp4")


def test_init_upload_storage_key_uses_uuid_segment(client):
    res = client.post("/api/uploads/init", json=_payload(filename="My Movie.mov"))
    assert res.status_code == 200, res.text
    body = res.json()
    parts = body["storage_key"].split("/")
    assert parts[0] == "originals"
    # uuid4().hex => 32 chars
    assert len(parts[1]) == 32
    assert all(ch in "0123456789abcdef" for ch in parts[1])
    # filename was sanitized but extension preserved
    assert parts[2].endswith(".mov")


def test_init_upload_rejects_unsupported_content_type(client):
    res = client.post(
        "/api/uploads/init",
        json=_payload(content_type="application/zip"),
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Unsupported file type"


def test_init_upload_rejects_zero_or_negative_size(client):
    res = client.post("/api/uploads/init", json=_payload(size_bytes=0))
    # Pydantic-level validation catches this before our handler runs.
    assert res.status_code == 422


def test_init_upload_rejects_oversized_files(client, monkeypatch):
    # Default max is 1024 MB from conftest; force it tiny here.
    monkeypatch.setattr(
        routes_upload.settings, "max_upload_size_mb", 1, raising=False
    )
    res = client.post(
        "/api/uploads/init",
        json=_payload(size_bytes=10 * 1024 * 1024),
    )
    assert res.status_code == 413
    assert res.json()["detail"] == "File too large"


def test_init_upload_returns_409_on_storage_key_collision(client):
    fixed_key = ("deadbeef" * 4, "originals/deadbeefdeadbeefdeadbeefdeadbeef/test.mp4")
    with patch.object(routes_upload, "_build_storage_key", return_value=fixed_key):
        first = client.post("/api/uploads/init", json=_payload(filename="test.mp4"))
        second = client.post("/api/uploads/init", json=_payload(filename="test.mp4"))

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text
    assert "retry" in second.json()["detail"].lower()


def test_init_upload_returns_500_when_signing_fails(client):
    """The signing helper translates infra errors into a clean HTTP 500.

    We force the inner ``get_object_store`` to raise so that
    ``_generate_upload_url``'s try/except surfaces the documented response
    instead of leaking a traceback.
    """

    class _BrokenStore:
        def generate_signed_upload_url(self, *_args, **_kwargs):
            raise RuntimeError("signing service offline")

    with patch.object(routes_upload, "get_object_store", return_value=_BrokenStore()), \
         patch.object(routes_upload, "_is_gcs_backend", return_value=True):
        res = client.post("/api/uploads/init", json=_payload())

    assert res.status_code == 500
    assert res.json()["detail"] == "Could not generate signed upload URL"
    # The internal exception text must not leak in the response body.
    assert "signing service offline" not in res.text


def test_init_upload_persists_video_metadata(client, db_session):
    res = client.post(
        "/api/uploads/init",
        json=_payload(filename="ocean.MP4", size_bytes=12345, title="Ocean"),
    )
    body = res.json()

    from app.db.models import VideoAsset

    video = db_session.get(VideoAsset, body["video_id"])
    assert video is not None
    assert video.status == "upload_pending"
    assert video.original_filename == "ocean.MP4"
    assert video.title == "Ocean"
    assert video.storage_key == body["storage_key"]
    assert video.file_size_bytes == 12345


def test_legacy_upload_endpoint_is_registered_and_deprecated():
    legacy = next(
        (r for r in routes_upload.router.routes if getattr(r, "path", "") == "/videos/upload"),
        None,
    )
    assert legacy is not None, "Legacy upload route is missing"
    assert "POST" in (legacy.methods or set())
    # FastAPI/Starlette's APIRoute exposes the deprecated flag.
    assert getattr(legacy, "deprecated", False) is True


# ---------------------------------------------------------------------------
# /api/uploads/complete + /api/uploads/direct (T1, T2)
# ---------------------------------------------------------------------------


def _do_init_and_put(client, filename: str = "video.mp4", body: bytes = b"x" * 32):
    init_res = client.post("/api/uploads/init", json=_payload(filename=filename))
    assert init_res.status_code == 200, init_res.text
    init_body = init_res.json()
    put_res = client.put(
        init_body["upload_url"],
        content=body,
        headers={"Content-Type": "video/mp4"},
    )
    assert put_res.status_code == 200, put_res.text
    return init_body


def test_local_direct_put_writes_bytes_in_dev_mode(client):
    init_body = _do_init_and_put(client, body=b"hello-cinetag")
    from app.storage import get_object_store

    store = get_object_store()
    assert store.object_exists(init_body["storage_key"])
    metadata = store.get_object_metadata(init_body["storage_key"])
    assert metadata["size"] == len(b"hello-cinetag")


def test_local_direct_put_rejects_non_originals_prefix(client):
    res = client.put(
        "/api/uploads/direct/secrets/passwd",
        content=b"pwned",
        headers={"Content-Type": "video/mp4"},
    )
    assert res.status_code == 400
    assert "prefix" in res.json()["detail"].lower()


def test_local_direct_put_rejects_path_traversal(client):
    # The Starlette router rewrites multi-segment paths through the
    # `{storage_key:path}` capture; we still defend by validating the prefix
    # and key contents.
    res = client.put(
        "/api/uploads/direct/originals/../etc/passwd",
        content=b"pwned",
        headers={"Content-Type": "video/mp4"},
    )
    # Either 400 from prefix/key validation or 404 from Starlette path
    # normalisation — never 200.
    assert res.status_code in (400, 404)


def test_local_direct_put_disabled_in_gcs_mode(client):
    with patch.object(routes_upload, "_is_gcs_backend", return_value=True):
        res = client.put(
            "/api/uploads/direct/originals/abc/test.mp4",
            content=b"x",
            headers={"Content-Type": "video/mp4"},
        )
    assert res.status_code == 400
    assert "signed gcs url" in res.json()["detail"].lower()


def test_complete_upload_happy_path_creates_processing_job(client, db_session):
    init_body = _do_init_and_put(client, filename="trailer.mp4", body=b"abcdef")
    with patch.object(routes_upload, "_assert_worker_broker_available", return_value=None), \
         patch.object(routes_upload, "publish_processing_job", return_value=None):
        res = client.post(
            "/api/uploads/complete",
            json={
                "video_id": init_body["video_id"],
                "storage_key": init_body["storage_key"],
            },
        )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["video_id"] == init_body["video_id"]
    assert payload["status"] == "queued"
    assert isinstance(payload["job_id"], int)

    from app.db.models import ProcessingJob, VideoAsset

    video = db_session.get(VideoAsset, init_body["video_id"])
    assert video is not None
    assert video.status == "uploaded"
    # complete should *not* have rewritten storage_key from the body.
    assert video.storage_key == init_body["storage_key"]
    assert video.file_size_bytes == len(b"abcdef")

    jobs = db_session.query(ProcessingJob).filter_by(video_id=video.id).all()
    assert len(jobs) == 1
    assert jobs[0].status == "queued"
    assert jobs[0].current_stage == "queued"


def test_complete_upload_is_idempotent_on_retry(client, db_session):
    init_body = _do_init_and_put(client)
    body = {
        "video_id": init_body["video_id"],
        "storage_key": init_body["storage_key"],
    }
    with patch.object(routes_upload, "_assert_worker_broker_available", return_value=None), \
         patch.object(routes_upload, "publish_processing_job", return_value=None):
        first = client.post("/api/uploads/complete", json=body)
        second = client.post("/api/uploads/complete", json=body)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["job_id"] == second.json()["job_id"]

    from app.db.models import ProcessingJob

    job_count = (
        db_session.query(ProcessingJob)
        .filter_by(video_id=init_body["video_id"])
        .count()
    )
    assert job_count == 1, "retrying complete must not create duplicate jobs"


def test_complete_upload_rejects_storage_key_hijack(client):
    # Two distinct init calls reserve two distinct storage_keys.
    a = _do_init_and_put(client, filename="a.mp4")
    b = _do_init_and_put(client, filename="b.mp4")
    # Try to "complete" video A pointing at video B's object.
    res = client.post(
        "/api/uploads/complete",
        json={"video_id": a["video_id"], "storage_key": b["storage_key"]},
    )
    assert res.status_code == 409
    assert "storage_key" in res.json()["detail"].lower()


def test_complete_upload_404_for_missing_video(client):
    res = client.post(
        "/api/uploads/complete",
        json={"video_id": 999_999, "storage_key": "originals/x/y.mp4"},
    )
    assert res.status_code == 404


def test_complete_upload_400_when_object_missing(client, db_session):
    init_res = client.post("/api/uploads/init", json=_payload())
    assert init_res.status_code == 200
    init_body = init_res.json()
    # NOTE: we deliberately skip the PUT step so the object never lands.
    res = client.post(
        "/api/uploads/complete",
        json={
            "video_id": init_body["video_id"],
            "storage_key": init_body["storage_key"],
        },
    )
    assert res.status_code == 400
    assert "not found" in res.json()["detail"].lower()


def test_complete_upload_fails_fast_when_broker_is_down(client, db_session):
    init_body = _do_init_and_put(client)
    with patch.object(
        routes_upload.run_pipeline.app,
        "connection_for_write",
        side_effect=RuntimeError("broker offline"),
    ):
        res = client.post(
            "/api/uploads/complete",
            json={
                "video_id": init_body["video_id"],
                "storage_key": init_body["storage_key"],
            },
        )
    assert res.status_code == 503, res.text
    assert "queue unavailable" in res.json()["detail"].lower()

    from app.db.models import ProcessingJob

    # No queued row should be created when enqueue cannot succeed.
    job_count = (
        db_session.query(ProcessingJob)
        .filter_by(video_id=init_body["video_id"])
        .count()
    )
    assert job_count == 0


def test_complete_upload_returns_503_when_publisher_fails(client):
    init_body = _do_init_and_put(client)
    with patch.object(routes_upload, "_assert_worker_broker_available", return_value=None), \
         patch.object(routes_upload, "publish_processing_job", side_effect=RuntimeError("queue down")):
        res = client.post(
            "/api/uploads/complete",
            json={
                "video_id": init_body["video_id"],
                "storage_key": init_body["storage_key"],
            },
        )
    assert res.status_code == 503
    assert "dispatch failed" in res.json()["detail"].lower()

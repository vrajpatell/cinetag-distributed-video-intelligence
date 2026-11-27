from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.db.models import AuditLog, ReviewNote


def path(video=11):
    return f"/api/videos/{video}/notes"


def draft(**fields):
    return {"request_id": str(uuid4()), "body": "Check the audio transition.", **fields}


def add(client, video=11, **fields):
    response = client.post(path(video), json=draft(**fields))
    assert response.status_code == 200, response.text
    return response.json()


def edit(client, note, **fields):
    return client.patch(
        f"{path(note['video_id'])}/{note['id']}", json={"revision": note["revision"], **fields}
    )


def test_creation_and_audit_share_the_transaction(client, catalog_db):
    note = add(client, body="  Inspect the cut. ", category="visual", position_ms=0)
    assert note["state"] == "open"
    assert note["revision"] == 1
    assert note["position_ms"] == 0
    assert note["body"] == "Inspect the cut."
    assert note["created_at"] == note["updated_at"]
    assert "request_hash" not in note
    audit = catalog_db.query(AuditLog).filter_by(action="review_note_create").one()
    assert audit.entity_id == note["id"]
    assert audit.after_json["video_id"] == 11
    assert audit.after_json["revision"] == 1
    assert "body" not in audit.after_json


def test_retry_same_creation_after_response_loss(client, catalog_db):
    body = draft()
    initial = client.post(path(), json=body).json()
    replay = client.post(path(), json=body)
    assert replay.status_code == 200
    assert replay.json() == initial
    assert catalog_db.query(ReviewNote).count() == 1
    assert catalog_db.query(AuditLog).count() == 1


def test_retry_preserves_later_edits(client, catalog_db):
    body = draft()
    saved = client.post(path(), json=body).json()
    edited = edit(client, saved, body="Updated wording").json()
    assert client.post(path(), json=body).json() == edited


def test_different_payload_with_same_request_id(client, catalog_db):
    body = draft()
    assert client.post(path(), json=body).status_code == 200
    assert client.post(path(), json={**body, "category": "audio"}).status_code == 409
    assert catalog_db.query(ReviewNote).count() == 1


def test_retry_identity_scoped_to_video(client, catalog_db):
    payload = draft()
    first = client.post(path(11), json=payload).json()
    second = client.post(path(12), json=payload).json()
    assert first["id"] != second["id"]
    assert first["video_id"] != second["video_id"]


@pytest.mark.parametrize(
    "fields",
    [
        {"body": ""},
        {"body": "    "},
        {"body": "a" * 4001},
        {"request_id": "not-a-uuid"},
        {"position_ms": -1},
        {"position_ms": 1.5},
        {"position_ms": 2**31},
        {"category": "internal"},
        {"state": "resolved"},
        {"revision": 5},
    ],
)
def test_create_rejects_malformed_input(client, catalog_db, fields):
    response = client.post(path(), json=draft(**fields))
    assert response.status_code == 422
    assert catalog_db.query(ReviewNote).count() == 0


def test_position_respects_known_duration(client, catalog_db):
    assert add(client, position_ms=12000)["position_ms"] == 12000
    assert client.post(path(), json=draft(position_ms=12001)).status_code == 422
    assert add(client, video=13, position_ms=99999)["position_ms"] == 99999


def test_edit_clear_position_and_preserve_other_fields(client, catalog_db):
    note = add(client, position_ms=400, category="audio")
    response = edit(client, note, position_ms=None, body="Word changed.")
    assert response.status_code == 200
    updated = response.json()
    assert updated["position_ms"] is None
    assert updated["category"] == "audio"
    assert updated["revision"] == 2
    assert updated["body"] == "Word changed."


def test_stale_edit_does_not_overwrite_state(client, catalog_db):
    original = add(client)
    resolved = edit(client, original, state="resolved").json()
    conflict = edit(client, original, body="Stale version")
    assert conflict.status_code == 409
    stored = client.get(path()).json()["items"][0]
    assert stored == resolved
    assert catalog_db.query(AuditLog).filter_by(action="review_note_edit").count() == 1
    reopened = edit(client, resolved, state="open").json()
    assert reopened["state"] == "open"
    assert reopened["revision"] == 3


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"body": None},
        {"body": " "},
        {"category": None},
        {"state": "archived"},
        {"position_ms": -5},
        {"position_ms": 500000},
        {"revision": 0, "body": "Edit"},
    ],
)
def test_invalid_edit_is_atomic(client, catalog_db, fields):
    note = add(client)
    assert edit(client, note, **fields).status_code == 422
    assert client.get(path()).json()["items"] == [note]
    assert catalog_db.query(AuditLog).count() == 1


def test_missing_note_or_video(client, catalog_db):
    saved = add(client)
    assert client.get(path(999)).status_code == 404
    assert client.post(path(999), json=draft()).status_code == 404
    assert (
        client.patch(
            f"{path(12)}/{saved['id']}", json={"revision": 1, "state": "resolved"}
        ).status_code
        == 404
    )
    assert (
        client.patch(f"{path()}/999", json={"revision": 1, "state": "resolved"}).status_code == 404
    )


def test_filter_counts_order_and_pagination(client, catalog_db):
    untimed = add(client)
    late = add(client, position_ms=6000)
    early = add(client, position_ms=500)
    resolved = edit(client, early, state="resolved").json()
    add(client, video=12)
    first = client.get(path(), params={"page_size": 1}).json()
    assert first["items"] == [resolved]
    assert first["total"] == 3
    assert first["open_count"] == 2
    assert first["resolved_count"] == 1
    opens = client.get(path(), params={"state": "open"}).json()
    assert opens["total"] == 2
    assert opens["items"] == [late, untimed]
    assert opens["resolved_count"] == 1
    assert client.get(path(), params={"state": "resolved", "page": 2}).json()["items"] == []


def test_service_can_read_but_review_role_required_to_write(client, catalog_db, monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_enabled", True)
    monkeypatch.setattr(get_settings(), "service_api_key", "worker-key")
    monkeypatch.setattr(get_settings(), "reviewer_api_key", "editor-key")
    service = {"X-API-Key": "worker-key"}
    reviewer = {"X-API-Key": "editor-key"}
    assert client.get(path(), headers=service).status_code == 200
    assert client.post(path(), headers=service, json=draft()).status_code == 401
    note = client.post(path(), headers=reviewer, json=draft()).json()
    assert (
        client.patch(
            f"{path()}/{note['id']}", headers=service, json={"revision": 1, "state": "resolved"}
        ).status_code
        == 401
    )


def test_review_notes_stay_out_of_delivery_exports(client, catalog_db):
    add(client, body="Internal editorial discussion")
    manifest = client.get("/api/videos/11/delivery/manifest")
    assert "Internal editorial discussion" not in manifest.text

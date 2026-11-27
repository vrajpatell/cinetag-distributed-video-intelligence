import pytest

from app.db.models import AuditLog
from app.tests.catalog.test_notes import add, edit, path


def history_url(note):
    return f"{path(note['video_id'])}/{note['id']}/history"


def test_history_reports_state_and_category_transitions(client, catalog_db):
    original = add(client, category="audio", position_ms=240)
    changed = edit(client, original, category="visual", position_ms=None).json()
    edit(client, changed, state="resolved")
    page = client.get(history_url(original)).json()
    assert [event["current"]["revision"] for event in page["items"]] == [3, 2, 1]
    newest, middle, first = page["items"]
    assert newest["current"]["state"] == "resolved"
    assert newest["previous"]["state"] == "open"
    assert middle["previous"]["position_ms"] == 240
    assert middle["current"]["position_ms"] is None
    assert middle["previous"]["category"] == "audio"
    assert middle["current"]["category"] == "visual"
    assert first["previous"] is None
    assert page["next_before"] is None


def test_cursor_history_stable_across_new_revisions(client, catalog_db):
    note = add(client)
    note = edit(client, note, body="Second version").json()
    note = edit(client, note, body="Third version").json()
    url = history_url(note)
    first = client.get(url, params={"page_size": 2}).json()
    assert [event["current"]["revision"] for event in first["items"]] == [3, 2]
    assert first["next_before"] == first["items"][-1]["id"]
    edit(client, note, category="transcript")
    next_page = client.get(url, params={"page_size": 2, "before": first["next_before"]}).json()
    assert [event["current"]["revision"] for event in next_page["items"]] == [1]
    assert next_page["next_before"] is None
    assert client.get(url).json()["items"][0]["current"]["revision"] == 4


def test_history_scoped_to_video_and_note(client, catalog_db):
    first = add(client, body="Restricted to the first note")
    other = add(client, video=12)
    catalog_db.add(
        AuditLog(
            actor="reviewer",
            entity_type="tag",
            entity_id=first["id"],
            action="tag_update",
            after_json={"tag_value": "Separate change"},
        )
    )
    catalog_db.commit()
    assert len(client.get(history_url(first)).json()["items"]) == 1
    assert client.get(f"{path(11)}/{other['id']}/history").status_code == 404
    assert client.get(f"{path(12)}/{first['id']}/history").status_code == 404
    response = client.get(history_url(first))
    assert first["body"] not in response.text
    assert "Separate change" not in response.text


@pytest.mark.parametrize("query", [{"before": 0}, {"page_size": 0}, {"page_size": 101}])
def test_history_limits(client, catalog_db, query):
    note = add(client)
    assert client.get(history_url(note), params=query).status_code == 422


def test_catalog_notes_can_be_triaged_across_videos(client, catalog_db):
    first = add(client, body="Repair crackle", category="audio", position_ms=0)
    second = add(client, video=12, body="Recheck audio levels", category="audio")
    edit(client, second, state="resolved")
    request = {
        "preset": "open",
        "filters": [{"field": "category", "operator": "eq", "value": "audio"}],
    }
    result = client.post("/api/catalog/notes/query", json=request).json()
    assert result["total"] == 1
    assert result["rows"][0]["video_id"] == first["video_id"]
    assert result["rows"][0]["cells"]["body"] == "Repair crackle"
    report = client.post("/api/catalog/notes/groups", json={"field": "state"}).json()
    assert report["total"] == 2
    assert {bucket["value"] for bucket in report["groups"]} == {"open", "resolved"}


def test_notes_export_only_advertised_fields(client, catalog_db):
    add(client, position_ms=1234)
    response = client.post(
        "/api/catalog/notes/export",
        json={
            "preset": "timed",
            "format": "json",
            "columns": ["video_id", "category", "position_ms"],
        },
    )
    assert response.json() == [{"video_id": 11, "category": "editorial", "position_ms": 1234}]
    assert (
        client.post("/api/catalog/notes/query", json={"columns": ["request_hash"]}).status_code
        == 422
    )

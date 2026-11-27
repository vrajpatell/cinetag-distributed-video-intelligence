import csv
import io
import json

import pytest

from app.catalog import query
from app.catalog.files import spreadsheet_value
from app.core.config import get_settings
from app.db.models import GeneratedTag


def test_quality_counts_match_drilldown(client, catalog_db):
    report = client.get("/api/catalog/quality").json()
    assert report["checked_at"].endswith("Z") or report["checked_at"].endswith("+00:00")
    checks = {(c["dataset"], c["preset"]): c for c in report["checks"]}
    assert checks["videos", "missing_summary"]["count"] == 1
    assert checks["videos", "missing_transcript"]["count"] == 1
    assert checks["videos", "published_pending"]["count"] == 1
    assert checks["scenes", "invalid_interval"]["count"] == 1
    assert checks["jobs", "unexplained_failure"]["count"] == 1
    for (dataset, preset), check in checks.items():
        result = client.post(f"/api/catalog/{dataset}/query", json={"preset": preset})
        assert result.status_code == 200
        assert result.json()["total"] == check["count"]


def test_empty_database_passes_all_checks(client):
    assert not any(c["count"] for c in client.get("/api/catalog/quality").json()["checks"])


def test_ready_to_publish_matches_review_gate(client, catalog_db):
    url = "/api/catalog/videos/query"
    assert [
        r["id"] for r in client.post(url, json={"preset": "ready_to_publish"}).json()["rows"]
    ] == [11]
    catalog_db.add(
        GeneratedTag(video_id=11, tag_type="mood", tag_value="Happy", status="pending_review")
    )
    catalog_db.commit()
    assert client.post(url, json={"preset": "ready_to_publish"}).json()["total"] == 0


def test_groups_include_null_and_tail(client, catalog_db):
    url = "/api/catalog/videos/groups"
    assert client.post(url, json={"field": "codec", "limit": 1}).json() == {
        "field": "codec",
        "total": 3,
        "groups": [{"value": "h264", "count": 2}],
        "remaining": 1,
    }
    assert client.post(url, json={"field": "codec", "limit": 2}).json()["groups"][-1] == {
        "value": None,
        "count": 1,
    }


def test_groups_respect_filters_and_preset(client, catalog_db):
    data = client.post(
        "/api/catalog/tags/groups",
        json={
            "field": "source",
            "search": "travel",
            "preset": "low_confidence",
            "filters": [{"field": "video_id", "operator": "eq", "value": "12"}],
        },
    ).json()
    assert data["total"] == 1
    assert data["groups"] == [{"value": "llm", "count": 1}]


def test_empty_group_selection(client):
    assert client.post("/api/catalog/tags/groups", json={"field": "status"}).json() == {
        "field": "status",
        "groups": [],
        "remaining": 0,
        "total": 0,
    }


def test_group_rejects_free_text(client):
    result = client.post("/api/catalog/transcripts/groups", json={"field": "text"})
    assert result.status_code == 422


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("=SUM(1,2)", "'=SUM(1,2)"),
        ("  +1", "'  +1"),
        ("-formula", "'-formula"),
        ("@test", "'@test"),
        ("\ttext", "'\ttext"),
        ("normal", "normal"),
        (-12, -12),
        (None, None),
    ],
)
def test_spreadsheet_strings(raw, expected):
    assert spreadsheet_value(raw) == expected


def test_csv_handles_unicode_formulas_quotes_and_linebreaks(client, catalog_db):
    title = '=HYPERLINK("café")\nsecond line'
    from app.db.models import VideoAsset

    catalog_db.get(VideoAsset, 11).title = title
    catalog_db.commit()
    res = client.post(
        "/api/catalog/videos/export",
        json={"preset": "ready_to_publish", "columns": ["title", "file_size_bytes"]},
    )
    assert res.status_code == 200
    assert res.headers["content-disposition"].endswith('filename="cinetag-videos.csv"')
    assert list(csv.reader(io.StringIO(res.content.decode("utf-8-sig")))) == [
        ["title", "file_size_bytes"],
        ["'" + title, "4096"],
    ]


@pytest.mark.parametrize("fmt", ["json", "ndjson"])
def test_exports_all_matches_in_view_order(client, catalog_db, fmt):
    response = client.post(
        "/api/catalog/videos/export",
        json={
            "format": fmt,
            "columns": ["id", "duration_seconds"],
            "page": 3,
            "page_size": 1,
            "sort": {"field": "id", "direction": "asc"},
        },
    )
    assert response.status_code == 200
    records = (
        response.json()
        if fmt == "json"
        else [json.loads(line) for line in response.text.splitlines()]
    )
    assert records == [
        {"id": 11, "duration_seconds": 12},
        {"id": 12, "duration_seconds": 8},
        {"id": 13, "duration_seconds": None},
    ]


def test_export_limit_applies_to_selection(client, catalog_db, monkeypatch):
    monkeypatch.setattr(query, "EXPORT_LIMIT", 2)
    response = client.post("/api/catalog/videos/export", json={"page_size": 1})
    assert response.status_code == 422
    assert "Narrow" in response.json()["detail"]
    assert client.post("/api/catalog/videos/export", json={"search": "Coast"}).status_code == 200


@pytest.mark.parametrize(("fmt", "text"), [("json", "[]\n"), ("ndjson", ""), ("csv", "id\r\n")])
def test_empty_export(client, fmt, text):
    response = client.post("/api/catalog/videos/export", json={"format": fmt, "columns": ["id"]})
    assert response.content.decode("utf-8-sig") == text


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/catalog/schema", None),
        ("GET", "/api/catalog/quality", None),
        ("POST", "/api/catalog/videos/query", {}),
        ("POST", "/api/catalog/videos/groups", {"field": "codec"}),
        ("POST", "/api/catalog/videos/export", {}),
        ("GET", "/api/videos/11/delivery", None),
        ("GET", "/api/videos/11/delivery/manifest", None),
        ("GET", "/api/videos/11/delivery/files/bundle", None),
    ],
)
def test_reporting_endpoints_honor_auth(client, catalog_db, monkeypatch, method, path, body):
    monkeypatch.setattr(get_settings(), "auth_enabled", True)
    monkeypatch.setattr(get_settings(), "reviewer_api_key", "local-test")
    assert client.request(method, path, json=body).status_code == 401
    assert (
        client.request(method, path, json=body, headers={"X-API-Key": "local-test"}).status_code
        == 200
    )

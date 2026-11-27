from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.catalog.query import DATASETS
from app.db.models import VideoAsset


def query(client: TestClient, dataset="videos", **payload):
    response = client.post(f"/api/catalog/{dataset}/query", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def record_ids(client, **payload):
    return [row["id"] for row in query(client, **payload)["rows"]]


def rule(field, operator, value=None):
    out = {"field": field, "operator": operator}
    if value is not None:
        out["value"] = value
    return out


def test_schema_describes_queryable_columns(client):
    response = client.get("/api/catalog/schema")
    assert response.status_code == 200
    schema = response.json()
    assert schema["export_limit"] > 0
    assert {r["id"] for r in schema["datasets"]} == set(DATASETS)
    for dataset in schema["datasets"]:
        fields = {field["id"]: field for field in dataset["fields"]}
        assert len(fields) == len(dataset["fields"])
        assert all(key in fields for key in dataset["default_columns"])
        assert dataset["default_sort"]["field"] in fields
        presets = [preset["id"] for preset in dataset["presets"]]
        assert len(set(presets)) == len(presets)
        assert all(col["operators"] for col in fields.values())


@pytest.mark.parametrize(
    ("key", "total"),
    [
        ("videos", 3),
        ("tags", 3),
        ("scenes", 3),
        ("frames", 1),
        ("transcripts", 1),
        ("jobs", 2),
        ("stages", 2),
        ("embeddings", 1),
    ],
)
def test_each_dataset_can_project_every_advertised_field(client, catalog_db, key, total):
    dataset = DATASETS[key]
    keys = list(dataset.by_key)
    data = query(client, key, columns=keys)
    assert data["columns"] == keys
    assert data["total"] == total
    assert len(data["rows"]) == total
    assert all(list(row["cells"]) == keys for row in data["rows"])
    assert all(row["video_id"] in (11, 12, 13) for row in data["rows"])


def test_default_sort_and_projection(client, catalog_db):
    result = query(client)
    assert result["columns"] == list(DATASETS["videos"].defaults)
    assert [row["id"] for row in result["rows"]] == [13, 12, 11]
    assert "storage_key" not in result["rows"][0]["cells"]


def test_projection_preserves_order_and_nulls(client, catalog_db):
    result = query(client, columns=["duration_seconds", "title", "id"])
    assert list(result["rows"][0]["cells"].items()) == [
        ("duration_seconds", None),
        ("title", None),
        ("id", 13),
    ]


def test_time_values_are_utc(client, catalog_db):
    rows = query(client, columns=["id", "created_at"])["rows"]
    assert datetime.fromisoformat(rows[0]["cells"]["created_at"]).utcoffset().total_seconds() == 0


@pytest.mark.parametrize(
    ("search", "ids"),
    [
        ("coast", [12, 11]),
        ("COAST", [12, 11]),
        ("%", [11]),
        ("_", [11]),
        ("!", [11]),
        ("_100%!", [11]),
        ("pending.mkv", [13]),
        ("estuary", [11]),
        ("unknown", []),
        ("", [13, 12, 11]),
    ],
)
def test_literal_search(client, catalog_db, search, ids):
    assert record_ids(client, search=search) == ids


@pytest.mark.parametrize(
    ("condition", "ids"),
    [
        (rule("title", "eq", "Coast road"), [12]),
        (rule("title", "ne", "Coast road"), [11]),
        (rule("title", "starts_with", "coast_"), [11]),
        (rule("title", "contains", "100%!"), [11]),
        (rule("title", "missing"), [13]),
        (rule("title", "present"), [12, 11]),
        (rule("summary", "missing"), [13, 12]),
        (rule("summary", "present"), [11]),
        (rule("duration_seconds", "gte", "8.5"), [11]),
        (rule("duration_seconds", "lte", "8"), [12]),
        (rule("duration_seconds", "missing"), [13]),
        (rule("file_size_bytes", "eq", "4096"), [11]),
        (rule("created_at", "gte", "2024-01-02T13:00:00+01:00"), [13, 12]),
        (rule("created_at", "lte", "2024-01-01T12:00:00Z"), [11]),
    ],
)
def test_typed_filters(client, catalog_db, condition, ids):
    assert record_ids(client, filters=[condition]) == ids


def test_composed_filters_search_and_preset(client, catalog_db):
    assert record_ids(
        client,
        search="coast",
        preset="missing_summary",
        filters=[rule("duration_seconds", "gte", "7"), rule("status", "eq", "published")],
    ) == [12]
    assert not record_ids(
        client, search="coast", preset="missing_summary", filters=[rule("width", "gte", "1920")]
    )


def test_tied_values_are_stable_across_pages(client, catalog_db):
    sort = {"field": "codec", "direction": "asc"}
    results = [query(client, page=i, page_size=1, sort=sort) for i in (1, 2, 3, 4)]
    assert [row["id"] for page in results for row in page["rows"]] == [11, 12, 13]
    assert all(page["total"] == 3 for page in results)
    assert results[-1]["rows"] == []


def test_descending_keeps_unknowns_last(client, catalog_db):
    assert record_ids(client, sort={"field": "duration_seconds", "direction": "desc"}) == [
        11,
        12,
        13,
    ]


def test_shows_record_without_optional_related_content(client, catalog_db):
    catalog_db.add(VideoAsset(id=14, original_filename="new.mp4", title="", storage_key="new"))
    catalog_db.commit()
    assert record_ids(client, search="new.mp4") == [14]
    assert query(client, "scenes", filters=[rule("video_id", "eq", "14")])["rows"] == []


@pytest.mark.parametrize(
    "body",
    [
        {"columns": []},
        {"columns": ["id", "id"]},
        {"columns": ["missing_column"]},
        {"page": 0},
        {"page_size": 101},
        {"filters": [rule("status", "eq", "x")] * 13},
        {"sort": {"field": "unknown"}},
        {"sort": {"field": "title", "direction": "first"}},
        {"filters": [rule("status", "gte", "a")]},
        {"filters": [rule("duration_seconds", "contains", "1")]},
        {"filters": [rule("duration_seconds", "eq", "nan")]},
        {"filters": [rule("frame_rate", "gte", "inf")]},
        {"filters": [rule("width", "eq", "1.5")]},
        {"filters": [rule("width", "eq", str(2**64))]},
        {"filters": [rule("created_at", "lte", "not a date")]},
        {"filters": [rule("id", "eq")]},
        {"filters": [rule("id", "missing", "unused")]},
        {"preset": "does_not_exist"},
        {"search": "x" * 257},
        {"unknown_option": True},
    ],
)
def test_rejects_incompatible_queries(client, body):
    response = client.post("/api/catalog/videos/query", json=body)
    assert response.status_code == 422


def test_unknown_dataset(client):
    response = client.post("/api/catalog/unknown/query", json={})
    assert response.status_code == 404

from math import ceil

import pytest

from app.db.models import VideoAsset


def stats(client, field, **selection):
    resp = client.post("/api/catalog/videos/distribution", json={"field": field, **selection})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_duration_summary_includes_missing(client, catalog_db):
    result = stats(client, "duration_seconds")
    assert result == {
        "field": "duration_seconds",
        "total": 3,
        "measured": 2,
        "missing": 1,
        "minimum": 8,
        "maximum": 12,
        "mean": 10,
        "median": 8,
        "p90": 12,
        "p95": 12,
    }


def test_percentiles_use_entire_selection(client, catalog_db):
    for index in range(1, 102):
        catalog_db.add(
            VideoAsset(
                title="Distribution sample",
                original_filename="sample.mp4",
                storage_key=f"dist/{index}",
                duration_seconds=index,
            )
        )
    catalog_db.commit()
    result = stats(client, "duration_seconds", search="Distribution sample")
    for name, level in (("median", 0.5), ("p90", 0.9), ("p95", 0.95)):
        assert result[name] == ceil(level * 101)
    assert result["mean"] == 51
    assert result["total"] == 101


def test_numeric_selection_may_be_all_null(client, catalog_db):
    result = stats(client, "duration_seconds", search="pending.mkv")
    assert result["total"] == result["missing"] == 1
    assert result["measured"] == 0
    for key in ("mean", "minimum", "maximum", "median", "p90", "p95"):
        assert result[key] is None


def test_zero_is_a_valid_measurement(client, catalog_db):
    catalog_db.get(VideoAsset, 13).file_size_bytes = 0
    catalog_db.commit()
    result = stats(
        client, "file_size_bytes", filters=[{"field": "id", "operator": "eq", "value": "13"}]
    )
    assert result["mean"] == 0
    assert result["median"] == 0
    assert result["missing"] == 0


def test_distribution_on_empty_selection(client):
    result = stats(client, "frame_rate")
    assert result["total"] == result["measured"] == result["missing"] == 0
    assert result["p95"] is None


def test_stage_latency_respects_join_and_filter(client, catalog_db):
    data = client.post(
        "/api/catalog/stages/distribution",
        json={
            "field": "duration_ms",
            "search": "Coast",
            "filters": [{"field": "status", "operator": "eq", "value": "completed"}],
        },
    ).json()
    assert data["measured"] == 1
    assert data["p95"] == 250


def test_all_advertised_measurements_work(client, catalog_db):
    schema = client.get("/api/catalog/schema").json()
    for dataset in schema["datasets"]:
        for field in dataset["fields"]:
            if field["measurable"]:
                response = client.post(
                    f"/api/catalog/{dataset['id']}/distribution", json={"field": field["id"]}
                )
                assert response.status_code == 200, (dataset["id"], field["id"], response.text)


@pytest.mark.parametrize("key", ["title", "id", "created_at", "unknown"])
def test_unsupported_measurement(client, key):
    assert client.post("/api/catalog/videos/distribution", json={"field": key}).status_code == 422

"""Exercise the installed CLI contract through the actual FastAPI routes."""

import io
import json
from datetime import UTC, datetime
from zipfile import ZipFile

import httpx
import pytest

from app.catalog.schema import QualityCount, QualityReport
from app.catalog_cli.client import CatalogClient, CatalogError
from app.catalog_cli.main import build_parser, main, run
from app.catalog_cli.output import atomic_write, clean_cell, text_table
from app.catalog_cli.snapshot import Trend, diff_reports, load_snapshot


@pytest.fixture()
def reports_client(client):
    def forward(request):
        upstream = client.request(
            request.method,
            request.url.raw_path.decode(),
            content=request.content,
            headers={"content-type": "application/json"},
        )
        return httpx.Response(
            upstream.status_code, content=upstream.content, headers=upstream.headers
        )

    with CatalogClient("http://testserver", transport=httpx.MockTransport(forward)) as api:
        yield api


def invoke(api, *args):
    options = build_parser().parse_args(args)
    stream = io.BytesIO()
    code = run(options, api, stream)
    return code, stream.getvalue()


def check(key, count, label="Finding"):
    return QualityCount(
        dataset="videos",
        dataset_label="Videos",
        preset=key,
        label=label,
        description="Sample check",
        count=count,
    )


def snapshot(*checks):
    return QualityReport(checked_at=datetime(2024, 1, 1, tzinfo=UTC), checks=list(checks))


def test_datasets_output(reports_client):
    code, data = invoke(reports_client, "datasets", "--json")
    assert code == 0
    assert {"videos", "scenes", "transcripts"} <= {d["id"] for d in json.loads(data)["datasets"]}


def test_describe_lists_machine_and_text_contract(reports_client):
    _, data = invoke(reports_client, "describe", "transcripts", "--json")
    dataset = json.loads(data)
    assert dataset["id"] == "transcripts"
    _, data = invoke(reports_client, "describe", "transcripts")
    assert b"Operators" in data and b"mock_text" in data
    with pytest.raises(CatalogError, match="Unknown dataset"):
        invoke(reports_client, "describe", "not-a-report")


def test_cli_query_composes_filters_and_projection(reports_client, catalog_db):
    _, data = invoke(
        reports_client,
        "query",
        "videos",
        "--search",
        "Coast",
        "--where",
        "duration_seconds:gte:7",
        "--where",
        "created_at:lte:2024-01-01T14:30:00Z",
        "--columns",
        "id,title",
        "--sort",
        "id",
        "--desc",
        "--json",
    )
    assert json.loads(data)["rows"] == [
        {"id": 11, "video_id": 11, "cells": {"id": 11, "title": "Coast_100%!"}}
    ]


def test_cli_query_pagination(reports_client, catalog_db):
    _, data = invoke(
        reports_client,
        "query",
        "videos",
        "--page-size",
        "1",
        "--page",
        "2",
        "--columns",
        "id",
        "--json",
    )
    page = json.loads(data)
    assert page["total"] == 3
    assert len(page["rows"]) == 1
    assert page["rows"][0]["id"] == 12


def test_cli_query_text_summary(reports_client, catalog_db):
    _, data = invoke(
        reports_client, "query", "videos", "--where", "summary:missing", "--columns", "id,title"
    )
    assert b"2 matching records" in data
    assert b"Coast road" in data


@pytest.mark.parametrize(
    ("flags", "message"),
    [
        (["--desc"], "requires --sort"),
        (["--where", "broken"], "FIELD:OP"),
        (["--where", "title:unknown:q"], "Unknown filter operator"),
    ],
)
def test_cli_rejects_invalid_filters(reports_client, flags, message):
    with pytest.raises(CatalogError, match=message):
        invoke(reports_client, "query", "videos", *flags)


def test_groups_limited_with_tail(reports_client, catalog_db):
    _, data = invoke(reports_client, "groups", "videos", "--by", "codec", "--limit", "1")
    assert b"Other groups" in data
    assert b"66.7%" in data


def test_cli_json_export_preserves_utf8(reports_client, catalog_db, tmp_path):
    out = tmp_path / "videos.json"
    code, data = invoke(
        reports_client,
        "export",
        "videos",
        "--columns",
        "id,title",
        "--format",
        "json",
        "--output",
        str(out),
    )
    assert code == 0 and data == b""
    assert [item["id"] for item in json.loads(out.read_text())] == [13, 12, 11]


def test_delivery_uses_original_bytes(reports_client, catalog_db, tmp_path):
    target = tmp_path / "asset.zip"
    code, _ = invoke(reports_client, "delivery", "11", "--file", "bundle", "-o", str(target))
    assert code == 0
    with ZipFile(target) as archive:
        assert "chapters.vtt" in archive.namelist()
    _, data = invoke(reports_client, "delivery", "11", "--json")
    assert json.loads(data)["approved_tags"] == 1


def test_export_failure_keeps_previous_file(reports_client, catalog_db, tmp_path):
    target = tmp_path / "chapter.vtt"
    target.write_text("previous result")
    with pytest.raises(CatalogError, match="409"):
        invoke(reports_client, "delivery", "13", "--file", "chapters", "-o", str(target))
    assert target.read_text() == "previous result"


def test_binary_delivery_requires_path(reports_client):
    with pytest.raises(CatalogError, match="--output"):
        invoke(reports_client, "delivery", "11", "--file", "bundle")


def test_cli_compare_emits_metrics(reports_client, catalog_db):
    _, data = invoke(reports_client, "compare", "11", "12", "--json")
    assert json.loads(data)["left"]["id"] == 11
    _, text = invoke(reports_client, "compare", "11", "12")
    assert b"Approved tags" in text


def test_diff_classifies_added_removed_and_changed():
    previous = snapshot(
        check("summary", 2), check("transcript", 3), check("retired", 100), check("frames", 0)
    )
    current = snapshot(
        check("summary", 4, "New name"), check("transcript", 1), check("new", 3), check("frames", 0)
    )
    result = diff_reports(previous, current)
    by_key = {change.preset: change for change in result.changes}
    assert by_key["summary"].trend == Trend.increased
    assert by_key["summary"].label == "New name"
    assert by_key["summary"].delta == 2
    assert by_key["transcript"].trend == Trend.improved
    assert by_key["transcript"].delta == -2
    assert by_key["frames"].trend == Trend.unchanged
    assert by_key["retired"].trend == Trend.removed
    assert by_key["retired"].after is None
    assert by_key["new"].trend == Trend.added
    assert by_key["new"].before is None
    assert result.has_increases()


def test_added_checks_do_not_trigger_regression_gate():
    result = diff_reports(snapshot(), snapshot(check("new", 9)))
    assert not result.has_increases()


def test_cli_snapshot_roundtrip_offline(reports_client, catalog_db, tmp_path):
    path = tmp_path / "quality.json"
    invoke(reports_client, "quality", "--json", "-o", str(path))
    report = load_snapshot(path)
    assert any(item.count > 0 for item in report.checks)
    changed = tmp_path / "after.json"
    report.checks[0].count += 1
    changed.write_text(report.model_dump_json())
    out = tmp_path / "changes.json"
    code = main(
        [
            "--api-url",
            "unused",
            "diff",
            str(path),
            "--current",
            str(changed),
            "--fail-on-increase",
            "--json",
            "-o",
            str(out),
        ]
    )
    assert code == 3
    changes = [c for c in json.loads(out.read_text())["changes"] if c["trend"] != "unchanged"]
    assert len(changes) == 1 and changes[0]["delta"] == 1


def test_live_diff_uses_current_counts(reports_client, catalog_db, tmp_path):
    out = tmp_path / "baseline.json"
    invoke(reports_client, "quality", "--json", "-o", str(out))
    code, data = invoke(reports_client, "diff", str(out), "--fail-on-increase")
    assert code == 0
    assert b"increased" not in data


@pytest.mark.parametrize("checks", [[check("x", 1), check("x", 2)], [check("x", -1)]])
def test_invalid_snapshot_counts(checks, tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text(snapshot(*checks).model_dump_json())
    with pytest.raises(CatalogError, match="Invalid or duplicate"):
        load_snapshot(path)


def test_invalid_snapshot_cli_exit(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    path.write_text('{"wrong":true}')
    assert main(["diff", str(path), "--current", str(path)]) == 1
    assert "Could not read quality snapshot" in capsys.readouterr().err


@pytest.mark.parametrize(
    "url",
    [
        "local:8000",
        "file:///tmp/a",
        "https://user@example.com",
        "https://x.test?a=1",
        "https://x.test/#part",
    ],
)
def test_client_rejects_ambiguous_base_urls(url):
    with pytest.raises(CatalogError):
        CatalogClient(url)


def test_base_path_and_auth_header():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"export_limit": 5, "datasets": []})

    with CatalogClient(
        "https://server.test/cinetag/", "test-key", transport=httpx.MockTransport(handler)
    ) as client:
        assert client.schema().export_limit == 5
    assert seen[0].url.path == "/cinetag/api/catalog/schema"
    assert seen[0].headers["X-API-Key"] == "test-key"


def test_client_validates_json_responses():
    with CatalogClient(
        "https://server.test",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text="not JSON")),
    ) as client, pytest.raises(CatalogError, match="Unexpected response"):
        client.schema()


def test_transport_error_display():
    def offline(request):
        raise httpx.ConnectError("Offline", request=request)

    with (
        CatalogClient("https://server.test", transport=httpx.MockTransport(offline)) as client,
        pytest.raises(CatalogError, match="Could not reach"),
    ):
        client.quality()


def test_failed_write_removes_temporary_file(tmp_path, monkeypatch):
    target = tmp_path / "report.json"
    target.write_bytes(b"old")

    def fail(*_):
        raise OSError("file in use")

    monkeypatch.setattr("app.catalog_cli.output.os.replace", fail)
    with pytest.raises(OSError, match="file in use"):
        atomic_write(target, b"new")
    assert list(tmp_path.iterdir()) == [target]
    assert target.read_bytes() == b"old"


def test_terminal_output_is_bounded_and_single_line():
    assert clean_cell("same\nline", 20) == "same line"
    assert clean_cell("long title", 5) == "long…"
    assert "\x1b" not in clean_cell("\x1b[31mcolor", 30)
    assert clean_cell(None, 5) == "—"
    assert len(text_table(["Title"], []).splitlines()) == 2

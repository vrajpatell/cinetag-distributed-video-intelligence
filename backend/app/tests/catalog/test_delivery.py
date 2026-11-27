import csv
import io
import json
from zipfile import ZipFile

import pytest

from app.db.models import SceneSegment, VideoAsset
from app.delivery.formats import ffescape, timecode
from app.delivery.manifest import chapters_from_scenes, millis


def download(client, kind, video_id=11):
    response = client.get(f"/api/videos/{video_id}/delivery/files/{kind}")
    assert response.status_code == 200, response.text[:300]
    return response


def segment(id, start, end, title=None):
    return SceneSegment(id=id, start_time_seconds=start, end_time_seconds=end, summary=title)


@pytest.mark.parametrize(
    ("seconds", "expected"), [(0, 0), (0.00049, 0), (0.0005, 1), (0.9995, 1000), (60.075, 60075)]
)
def test_timestamp_rounding(seconds, expected):
    assert millis(seconds) == expected


@pytest.mark.parametrize(
    ("ms", "text"),
    [
        (0, "00:00:00.000"),
        (123, "00:00:00.123"),
        (60001, "00:01:00.001"),
        (3661999, "01:01:01.999"),
        (360000001, "100:00:00.001"),
    ],
)
def test_webvtt_timestamps(ms, text):
    assert timecode(ms) == text


@pytest.mark.parametrize(
    ("start", "end"), [(-1, 1), (0, 0), (2, 1), (float("nan"), 2), (0, float("inf"))]
)
def test_invalid_intervals_have_notices(start, end):
    chapters, notices = chapters_from_scenes([segment(42, start, end)], None)
    assert chapters == []
    assert [n.code for n in notices] == ["invalid_interval"]
    assert notices[0].scene_id == 42


def test_trim_overlap_and_duration_without_changing_source():
    rows = [
        segment(1, 0, 4, "Intro"),
        segment(2, 2, 6, "Next\nsection"),
        segment(3, 4, 5),
        segment(4, 8, 15),
    ]
    chapters, notices = chapters_from_scenes(rows, 10)
    assert [(c.start_ms, c.end_ms, c.title) for c in chapters] == [
        (0, 4000, "Intro"),
        (4000, 6000, "Next section"),
        (8000, 10000, "Scene 3"),
    ]
    assert {(n.scene_id, n.code) for n in notices} == {
        (2, "overlap"),
        (3, "overlap"),
        (3, "empty_interval"),
        (4, "past_duration"),
    }
    assert rows[1].start_time_seconds == 2
    assert rows[-1].end_time_seconds == 15


def test_skip_interval_shorter_than_timestamp_resolution():
    chapters, notices = chapters_from_scenes([segment(8, 4.0001, 4.0002)], None)
    assert chapters == []
    assert notices[0].code == "empty_interval"


def test_missing_duration_preserves_exportable_intervals():
    chapters, notices = chapters_from_scenes([segment(1, 0, 2.5), segment(2, 4, 10)], None)
    assert notices == []
    assert chapters[-1].end_ms == 10000


def test_manifest_excludes_nonapproved_tags_and_storage_details(client, catalog_db):
    manifest = client.get("/api/videos/11/delivery/manifest").json()
    assert manifest["media"]["filename"] == "coast.mp4"
    assert manifest["media"]["duration_seconds"] == 12
    assert [tag["id"] for tag in manifest["tags"]] == [31]
    assert "storage_key" not in manifest["media"]
    assert "private/" not in json.dumps(manifest)
    assert manifest["chapters"][0]["scene_id"] == 21
    assert manifest["transcript"]["language"] == "en"


def test_preview_lists_available_sidecars(client, catalog_db):
    result = client.get("/api/videos/11/delivery").json()
    assert result["approved_tags"] == 1
    assert result["chapters"] == 2
    assert result["transcript_available"] is True
    assert all(item["available"] and item["reason"] is None for item in result["files"])


def test_partial_delivery_is_explicit(client, catalog_db):
    preview = client.get("/api/videos/12/delivery").json()
    files = {item["format"]: item for item in preview["files"]}
    assert {key for key, item in files.items() if item["available"]} == {"manifest", "bundle"}
    assert preview["notices"][0]["code"] == "invalid_interval"
    assert files["tags"]["reason"] == "No approved tags."
    for key in ("tags", "ffmetadata", "chapters", "transcript", "cue-sheet"):
        res = client.get(f"/api/videos/12/delivery/files/{key}")
        assert res.status_code == 409
        assert res.json()["detail"] == files[key]["reason"]


def test_bundle_contents_match_individual_downloads(client, catalog_db):
    preview = client.get("/api/videos/11/delivery").json()
    response = download(client, "bundle")
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"].endswith('filename="cinetag-11-delivery.zip"')
    with ZipFile(io.BytesIO(response.content)) as archive:
        members = [f for f in preview["files"] if f["format"] != "bundle"]
        assert sorted(archive.namelist()) == sorted(f["filename"] for f in members)
        for f in members:
            assert archive.read(f["filename"]) == download(client, f["format"]).content
    assert download(client, "bundle").content == response.content


def test_empty_bundle_has_manifest(client, catalog_db):
    with ZipFile(io.BytesIO(download(client, "bundle", 13).content)) as archive:
        assert archive.namelist() == ["manifest.json"]
        assert json.loads(archive.read("manifest.json"))["media"]["video_id"] == 13


def test_transcript_download_preserves_lines(client, catalog_db):
    response = download(client, "transcript")
    assert response.text == "The estuary\nopens into the sea."


def test_chapter_track_contains_sorted_and_escaped_titles(client, catalog_db):
    text = download(client, "chapters").text
    assert text.startswith("WEBVTT\n\n")
    assert "21\n00:00:00.000 --> 00:00:07.125\n=Estuary" in text
    assert "20\n00:00:07.125 --> 00:00:12.000\nBoats &amp; dunes" in text
    assert text.index("21\n") < text.index("20\n")


def test_ffmetadata_rounds_to_same_millisecond_timebase(client, catalog_db):
    text = download(client, "ffmetadata").text
    assert text.startswith(";FFMETADATA1\n")
    assert text.count("[CHAPTER]") == 2
    assert "TIMEBASE=1/1000\nSTART=7125\nEND=12000" in text
    assert "title=\\=Estuary" in text


def test_ffmetadata_escapes_field_delimiters():
    assert ffescape("x=y;z#k\\end\nnext") == "x\\=y\\;z\\#k\\\\end next"


def test_csv_sidecars(client, catalog_db):
    tags = list(csv.DictReader(io.StringIO(download(client, "tags").content.decode("utf-8-sig"))))
    assert [(t["value"], t["source"]) for t in tags] == [("Travel", "manual")]
    cues = list(
        csv.DictReader(io.StringIO(download(client, "cue-sheet").content.decode("utf-8-sig")))
    )
    assert [row["duration_ms"] for row in cues] == ["7125", "4875"]
    assert cues[0]["title"] == "'=Estuary"


def test_missing_asset_and_unsupported_format(client):
    assert client.get("/api/videos/999/delivery").status_code == 404
    assert client.get("/api/videos/999/delivery/manifest").status_code == 404


def test_filename_does_not_control_zip_member_paths(client, catalog_db):
    catalog_db.get(VideoAsset, 11).original_filename = "clips/été.mov"
    catalog_db.commit()
    with ZipFile(io.BytesIO(download(client, "bundle").content)) as archive:
        assert all("/" not in name for name in archive.namelist())

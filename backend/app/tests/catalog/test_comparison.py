import pytest

from app.catalog.comparison import Relation, relation
from app.db.models import GeneratedTag, Transcript


def compare(client, left=11, right=12):
    res = client.get("/api/catalog/compare", params={"left": left, "right": right})
    assert res.status_code == 200, res.text
    return res.json()


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (None, None, Relation.unknown),
        (None, 0, Relation.right_only),
        ("", None, Relation.left_only),
        (0, 0.0, Relation.equal),
        ("h264", "h265", Relation.different),
    ],
)
def test_relation_includes_zero(a, b, expected):
    assert relation(a, b) == expected


def test_media_and_pipeline_measures(client, catalog_db):
    data = compare(client)
    metrics = {m["id"]: m for m in data["metrics"]}
    assert data["left"] == {"id": 11, "title": "Coast_100%!"}
    assert data["right"] == {"id": 12, "title": "Coast road"}
    assert metrics["codec"]["relation"] == "equal"
    assert metrics["duration"]["relation"] == "different"
    assert metrics["chapters"]["left"] == 2
    assert metrics["chapters"]["right"] == 0
    assert metrics["coverage"]["left"] == 1
    assert metrics["mean_chapter"]["left"] == 6
    assert metrics["words"]["right"] is None
    assert data["speech"]["vocabulary_similarity"] is None


def test_tag_matches_use_type_and_normalized_value(client, catalog_db):
    for kind, value in [("genre", " travel "), ("genre", "ＴＲＡＶＥＬ"), ("theme", "Travel")]:
        catalog_db.add(
            GeneratedTag(
                video_id=12, tag_type=kind, tag_value=value, status="approved", source="manual"
            )
        )
    catalog_db.commit()
    tags = compare(client)["tags"]
    assert tags["similarity"] == 0.5
    assert tags["shared"] == [{"type": "genre", "value": "Travel"}]
    assert tags["left_only"] == []
    assert tags["right_only"] == [{"type": "theme", "value": "Travel"}]


def test_unreviewed_tags_do_not_contribute_to_similarity(client, catalog_db):
    tags = compare(client)["tags"]
    assert tags["shared"] == []
    assert tags["right_only"] == []
    assert tags["left_only"] == [{"type": "genre", "value": "Travel"}]
    assert tags["similarity"] == 0


def test_compare_without_labels_or_transcripts(client, catalog_db):
    data = compare(client, 12, 13)
    assert data["tags"]["similarity"] is None
    assert data["speech"]["frequent_shared"] == []
    assert data["right"]["title"] == "pending.mkv"


def test_casefolded_speech_jaccard_and_counts(client, catalog_db):
    catalog_db.query(Transcript).filter_by(video_id=11).one().text = "Boots, boots. Sea | પાણી"
    catalog_db.add(Transcript(video_id=12, text="BOOTS sea sea પાણી Hill", language="en"))
    catalog_db.commit()
    speech = compare(client)["speech"]
    assert speech["unique_left"] == 3
    assert speech["unique_right"] == 4
    assert speech["shared_words"] == 3
    assert speech["vocabulary_similarity"] == 0.75
    assert speech["frequent_shared"] == [
        {"word": "boots", "left_count": 2, "right_count": 1},
        {"word": "sea", "left_count": 1, "right_count": 2},
        {"word": "પાણી", "left_count": 1, "right_count": 1},
    ]


def test_comparison_is_symmetric(client, catalog_db):
    forward = compare(client)
    reverse = compare(client, 12, 11)
    assert forward["tags"]["similarity"] == reverse["tags"]["similarity"]
    assert forward["tags"]["left_only"] == reverse["tags"]["right_only"]
    for before, after in zip(forward["metrics"], reverse["metrics"], strict=True):
        assert before["left"] == after["right"]
        assert before["right"] == after["left"]


@pytest.mark.parametrize(
    ("left", "right", "code"),
    [(11, 11, 422), (-1, 11, 422), (11, 0, 422), (11, 999, 404), (999, 11, 404)],
)
def test_invalid_comparisons(client, catalog_db, left, right, code):
    assert (
        client.get("/api/catalog/compare", params={"left": left, "right": right}).status_code
        == code
    )

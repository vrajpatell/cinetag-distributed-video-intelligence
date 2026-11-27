"""Compare two video records and show the basis of each similarity measure."""

from __future__ import annotations

import unicodedata
from collections import Counter
from enum import StrEnum

from pydantic import BaseModel

from app.catalog.schema import CellValue, Kind
from app.delivery.schema import DeliveryManifest


class Relation(StrEnum):
    equal = "equal"
    different = "different"
    left_only = "left_only"
    right_only = "right_only"
    unknown = "unknown"


class Metric(BaseModel):
    id: str
    group: str
    label: str
    kind: Kind
    left: CellValue
    right: CellValue
    relation: Relation


class ComparedAsset(BaseModel):
    id: int
    title: str


class LabelMatch(BaseModel):
    type: str
    value: str


class TagComparison(BaseModel):
    shared: list[LabelMatch]
    left_only: list[LabelMatch]
    right_only: list[LabelMatch]
    similarity: float | None


class VocabularyMatch(BaseModel):
    word: str
    left_count: int
    right_count: int


class SpeechComparison(BaseModel):
    unique_left: int
    unique_right: int
    shared_words: int
    vocabulary_similarity: float | None
    frequent_shared: list[VocabularyMatch]


class Comparison(BaseModel):
    left: ComparedAsset
    right: ComparedAsset
    metrics: list[Metric]
    tags: TagComparison
    speech: SpeechComparison


def relation(left, right):
    if left is None and right is None:
        return Relation.unknown
    if left is None:
        return Relation.right_only
    if right is None:
        return Relation.left_only
    return Relation.equal if left == right else Relation.different


def normalize_label(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def label_set(manifest):
    labels = {}
    for tag in manifest.tags:
        kind = normalize_label(tag.type)
        value = normalize_label(tag.value)
        if value:
            labels.setdefault(
                (kind.casefold(), value.casefold()), LabelMatch(type=kind, value=value)
            )
    return labels


def compare_tags(left, right) -> TagComparison:
    left_tags = label_set(left)
    right_tags = label_set(right)
    shared = left_tags.keys() & right_tags.keys()
    union = left_tags.keys() | right_tags.keys()
    return TagComparison(
        shared=[left_tags[key] for key in sorted(shared)],
        left_only=[left_tags[key] for key in sorted(left_tags.keys() - right_tags.keys())],
        right_only=[right_tags[key] for key in sorted(right_tags.keys() - left_tags.keys())],
        similarity=len(shared) / len(union) if union else None,
    )


def vocabulary(manifest):
    if manifest.transcript is None:
        return Counter()
    text = unicodedata.normalize("NFKC", manifest.transcript.text).casefold()
    # Keep combining marks with the preceding letters (e.g. Gujarati, Hindi).
    words = []
    token = []
    for char in text:
        if char.isalnum() or (token and unicodedata.category(char).startswith("M")):
            token.append(char)
        elif token:
            words.append("".join(token))
            token.clear()
    if token:
        words.append("".join(token))
    return Counter(words)


def compare_speech(left, right, left_words, right_words) -> SpeechComparison:
    shared = left_words.keys() & right_words.keys()
    union = left_words.keys() | right_words.keys()
    can_compare = left.transcript is not None and right.transcript is not None
    ranked = sorted(shared, key=lambda w: (-min(left_words[w], right_words[w]), w))
    return SpeechComparison(
        unique_left=len(left_words),
        unique_right=len(right_words),
        shared_words=len(shared),
        vocabulary_similarity=len(shared) / len(union) if union and can_compare else None,
        frequent_shared=[
            VocabularyMatch(word=w, left_count=left_words[w], right_count=right_words[w])
            for w in ranked[:20]
        ],
    )


def measurements(manifest, words):
    media = manifest.media
    chapters = manifest.chapters
    covered = sum(c.end_ms - c.start_ms for c in chapters)
    transcript = manifest.transcript
    return {
        "status": media.status,
        "duration": media.duration_seconds,
        "width": media.width,
        "height": media.height,
        "frame_rate": media.frame_rate,
        "bitrate": media.bitrate,
        "codec": media.codec,
        "size": media.file_size_bytes,
        "chapters": len(chapters),
        "coverage": min(1, covered / (media.duration_seconds * 1000))
        if media.duration_seconds and media.duration_seconds > 0
        else None,
        "mean_chapter": covered / len(chapters) / 1000 if chapters else None,
        "approved_tags": len(manifest.tags),
        "tag_types": len({t.type.casefold() for t in manifest.tags}),
        "words": sum(words.values()) if transcript else None,
        "language": transcript.language if transcript else None,
        "transcript_confidence": transcript.confidence if transcript else None,
    }


METRICS = (
    ("status", "Media", "Catalog status", Kind.text),
    ("duration", "Media", "Duration", Kind.duration),
    ("width", "Media", "Width (px)", Kind.integer),
    ("height", "Media", "Height (px)", Kind.integer),
    ("frame_rate", "Media", "Frames per second", Kind.decimal),
    ("bitrate", "Media", "Bitrate (bps)", Kind.integer),
    ("codec", "Media", "Codec", Kind.text),
    ("size", "Media", "File size", Kind.size),
    ("chapters", "Scenes", "Exportable chapters", Kind.integer),
    ("coverage", "Scenes", "Timeline covered", Kind.confidence),
    ("mean_chapter", "Scenes", "Mean chapter length", Kind.duration),
    ("approved_tags", "Tags", "Approved tags", Kind.integer),
    ("tag_types", "Tags", "Tag types", Kind.integer),
    ("words", "Transcript", "Word tokens", Kind.integer),
    ("language", "Transcript", "Language", Kind.text),
    ("transcript_confidence", "Transcript", "Confidence", Kind.confidence),
)


def compare(left: DeliveryManifest, right: DeliveryManifest) -> Comparison:
    left_words = vocabulary(left)
    right_words = vocabulary(right)
    first = measurements(left, left_words)
    second = measurements(right, right_words)
    return Comparison(
        left=ComparedAsset(id=left.media.video_id, title=left.media.title or left.media.filename),
        right=ComparedAsset(
            id=right.media.video_id, title=right.media.title or right.media.filename
        ),
        metrics=[
            Metric(
                id=key,
                group=group,
                label=label,
                kind=kind,
                left=first[key],
                right=second[key],
                relation=relation(first[key], second[key]),
            )
            for key, group, label, kind in METRICS
        ],
        tags=compare_tags(left, right),
        speech=compare_speech(left, right, left_words, right_words),
    )

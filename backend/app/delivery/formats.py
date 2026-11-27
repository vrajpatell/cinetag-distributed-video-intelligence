"""Metadata sidecars suitable for editorial review and local media tooling."""

from __future__ import annotations

import csv
import html
import io
import zipfile
from dataclasses import dataclass

from app.catalog.files import spreadsheet_value
from app.delivery.schema import DeliveryFormat, DeliveryManifest, DeliveryPreview, FileInfo


@dataclass(frozen=True)
class Sidecar:
    name: str
    mime: str


SIDECARS = {
    DeliveryFormat.manifest: Sidecar("manifest.json", "application/json"),
    DeliveryFormat.transcript: Sidecar("transcript.txt", "text/plain"),
    DeliveryFormat.chapters: Sidecar("chapters.vtt", "text/vtt"),
    DeliveryFormat.ffmetadata: Sidecar("chapters.ffmeta", "text/plain"),
    DeliveryFormat.tags: Sidecar("approved-tags.csv", "text/csv"),
    DeliveryFormat.cue_sheet: Sidecar("cue-sheet.csv", "text/csv"),
    DeliveryFormat.bundle: Sidecar("delivery.zip", "application/zip"),
}


def availability(manifest: DeliveryManifest, fmt: DeliveryFormat) -> str | None:
    if fmt == DeliveryFormat.transcript and manifest.transcript is None:
        return "No transcript available."
    if (
        fmt in (DeliveryFormat.chapters, DeliveryFormat.ffmetadata, DeliveryFormat.cue_sheet)
        and not manifest.chapters
    ):
        return "No valid scene intervals."
    if fmt == DeliveryFormat.tags and not manifest.tags:
        return "No approved tags."
    return None


def preview(manifest: DeliveryManifest) -> DeliveryPreview:
    files = []
    for fmt, file in SIDECARS.items():
        reason = availability(manifest, fmt)
        files.append(
            FileInfo(
                format=fmt,
                filename=file.name,
                media_type=file.mime,
                available=reason is None,
                reason=reason,
            )
        )
    return DeliveryPreview(
        video_id=manifest.media.video_id,
        title=manifest.media.title or manifest.media.filename,
        approved_tags=len(manifest.tags),
        chapters=len(manifest.chapters),
        transcript_available=manifest.transcript is not None,
        files=files,
        notices=manifest.notices,
    )


def timecode(ms: int) -> str:
    seconds, fraction = divmod(ms, 1000)
    minutes, second = divmod(seconds, 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour:02}:{minute:02}:{second:02}.{fraction:03}"


def vtt(manifest: DeliveryManifest) -> str:
    parts = ["WEBVTT\n"]
    for chapter in manifest.chapters:
        parts.append(
            f"{chapter.scene_id}\n"
            f"{timecode(chapter.start_ms)} --> {timecode(chapter.end_ms)}\n"
            f"{html.escape(chapter.title, quote=False)}\n"
        )
    return "\n".join(parts)


def ffescape(value: str) -> str:
    single_line = " ".join(value.splitlines())
    return "".join("\\" + char if char in "\\;#=" else char for char in single_line)


def ffmetadata(manifest: DeliveryManifest) -> str:
    lines = [";FFMETADATA1"]
    if manifest.media.title:
        lines.append("title=" + ffescape(manifest.media.title))
    for chapter in manifest.chapters:
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={chapter.start_ms}",
                f"END={chapter.end_ms}",
                "title=" + ffescape(chapter.title),
            ]
        )
    return "\n".join(lines) + "\n"


def csv_bytes(header, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(header)
    for row in rows:
        writer.writerow(spreadsheet_value(item) for item in row)
    return stream.getvalue().encode("utf-8-sig")


def render(manifest: DeliveryManifest, fmt: DeliveryFormat) -> bytes:
    reason = availability(manifest, fmt)
    if reason:
        raise ValueError(reason)
    if fmt == DeliveryFormat.manifest:
        return (manifest.model_dump_json(indent=2) + "\n").encode()
    if fmt == DeliveryFormat.transcript:
        return manifest.transcript.text.encode()
    if fmt == DeliveryFormat.chapters:
        return vtt(manifest).encode()
    if fmt == DeliveryFormat.ffmetadata:
        return ffmetadata(manifest).encode()
    if fmt == DeliveryFormat.tags:
        return csv_bytes(
            ("tag_id", "type", "value", "source", "confidence", "rationale"),
            (
                (tag.id, tag.type, tag.value, tag.source, tag.confidence, tag.rationale)
                for tag in manifest.tags
            ),
        )
    if fmt == DeliveryFormat.cue_sheet:
        return csv_bytes(
            ("scene_id", "start", "end", "duration_ms", "title"),
            (
                (
                    c.scene_id,
                    timecode(c.start_ms),
                    timecode(c.end_ms),
                    c.end_ms - c.start_ms,
                    c.title,
                )
                for c in manifest.chapters
            ),
        )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for kind, file in SIDECARS.items():
            if kind == DeliveryFormat.bundle or availability(manifest, kind):
                continue
            # Stable metadata makes repeated exports of the same asset comparable.
            archive.writestr(
                zipfile.ZipInfo(file.name),
                render(manifest, kind),
                compress_type=zipfile.ZIP_DEFLATED,
            )
    return output.getvalue()

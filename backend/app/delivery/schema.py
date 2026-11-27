from enum import StrEnum

from pydantic import BaseModel, Field


class DeliveryFormat(StrEnum):
    manifest = "manifest"
    transcript = "transcript"
    chapters = "chapters"
    ffmetadata = "ffmetadata"
    tags = "tags"
    cue_sheet = "cue-sheet"
    bundle = "bundle"


class MediaInfo(BaseModel):
    video_id: int
    title: str | None
    filename: str
    status: str
    summary: str | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    codec: str | None
    bitrate: int | None
    frame_rate: float | None
    file_size_bytes: int | None


class DeliveredTag(BaseModel):
    id: int
    type: str
    value: str
    source: str
    confidence: float | None
    rationale: str | None


class Chapter(BaseModel):
    scene_id: int
    start_ms: int
    end_ms: int
    title: str


class DeliveryTranscript(BaseModel):
    text: str
    language: str | None
    confidence: float | None


class Notice(BaseModel):
    code: str
    message: str
    scene_id: int | None = None


class DeliveryManifest(BaseModel):
    version: int = 1
    media: MediaInfo
    transcript: DeliveryTranscript | None
    tags: list[DeliveredTag]
    chapters: list[Chapter]
    notices: list[Notice]


class FileInfo(BaseModel):
    format: DeliveryFormat
    filename: str
    media_type: str
    available: bool
    reason: str | None = None


class DeliveryPreview(BaseModel):
    video_id: int
    title: str
    approved_tags: int = Field(ge=0)
    chapters: int = Field(ge=0)
    transcript_available: bool
    files: list[FileInfo]
    notices: list[Notice]

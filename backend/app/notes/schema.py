from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    model_validator,
)


class Category(StrEnum):
    editorial = "editorial"
    audio = "audio"
    visual = "visual"
    transcript = "transcript"
    tags = "tags"


class State(StrEnum):
    open = "open"
    resolved = "resolved"


Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
Position = Annotated[int, Field(ge=0, le=2**31 - 1, strict=True)]


class CreateNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    body: Body
    category: Category = Category.editorial
    position_ms: Position | None = None


class EditNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    body: Body | None = None
    category: Category | None = None
    state: State | None = None
    position_ms: Position | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        changes = self.model_fields_set - {"revision"}
        if not changes:
            raise ValueError("Supply at least one change")
        for key in changes - {"position_ms"}:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null")
        return self


class Note(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    video_id: int
    category: Category
    state: State
    body: str
    position_ms: int | None
    revision: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def utc_timestamp(self, value: datetime):
        return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()


class NotePage(BaseModel):
    items: list[Note]
    total: int
    page: int
    page_size: int
    open_count: int
    resolved_count: int


class RevisionMetadata(BaseModel):
    revision: int
    state: State
    category: Category
    position_ms: int | None


class RevisionEvent(BaseModel):
    id: int
    timestamp: datetime
    previous: RevisionMetadata | None
    current: RevisionMetadata


class NoteHistory(BaseModel):
    items: list[RevisionEvent]
    next_before: int | None

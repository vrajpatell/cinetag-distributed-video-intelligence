from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import RequireReviewerOrAdmin, RequireViewerOrAbove
from app.db.session import get_db
from app.notes import service
from app.notes.schema import CreateNote, EditNote, Note, NotePage, NoteHistory, State

router = APIRouter(prefix="/videos/{video_id}/notes", tags=["review notes"])
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=NotePage, operation_id="list_video_notes")
def list_video_notes(
    video_id: int,
    db: Database,
    _auth: RequireViewerOrAbove,
    state: State | None = None,
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    return service.list_notes(db, video_id, state, page, page_size)


@router.post("", response_model=Note, operation_id="create_video_note")
def create_video_note(
    video_id: int, payload: CreateNote, db: Database, _auth: RequireReviewerOrAdmin
):
    return service.create(db, video_id, payload)


@router.patch("/{note_id}", response_model=Note, operation_id="edit_video_note")
def edit_video_note(
    video_id: int, note_id: int, payload: EditNote, db: Database, _auth: RequireReviewerOrAdmin
):
    return service.edit(db, video_id, note_id, payload)


@router.get("/{note_id}/history", response_model=NoteHistory, operation_id="get_note_history")
def get_note_history(
    video_id: int,
    note_id: int,
    db: Database,
    _auth: RequireViewerOrAbove,
    before: Annotated[int | None, Query(gt=0)] = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
):
    return service.history(db, video_id, note_id, before, page_size)

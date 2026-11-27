import hashlib
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AuditLog, ReviewNote, VideoAsset
from app.notes.schema import CreateNote, EditNote, Note, NoteHistory, NotePage, RevisionEvent, State


def get_asset(db: Session, video_id: int):
    video = db.get(VideoAsset, video_id)
    if video is None:
        raise HTTPException(404, "Video not found")
    return video


def check_position(video, position):
    if (
        position is not None
        and video.duration_seconds is not None
        and video.duration_seconds > 0
        and position > round(video.duration_seconds * 1000)
    ):
        raise HTTPException(422, "Note position exceeds the video duration")


def timestamp():
    return datetime.now(UTC).replace(tzinfo=None)


def audit(db, row, action, previous=None):
    # The note table already contains the text. Keep audit metadata focused on changes.
    db.add(
        AuditLog(
            actor="reviewer",
            action=action,
            entity_type="review_note",
            entity_id=row.id,
            before_json=previous,
            after_json=summary(row),
        )
    )


def summary(row):
    return {
        "video_id": row.video_id,
        "state": row.state,
        "category": row.category,
        "revision": row.revision,
        "position_ms": row.position_ms,
    }


def create(db: Session, video_id: int, payload: CreateNote):
    video = get_asset(db, video_id)
    digest = hashlib.sha256(payload.model_dump_json(exclude={"request_id"}).encode()).hexdigest()
    previous = select(ReviewNote).where(
        ReviewNote.video_id == video_id, ReviewNote.request_id == str(payload.request_id)
    )

    def replay(row):
        if row.request_hash != digest:
            raise HTTPException(409, "This request ID already belongs to a different note")
        return Note.model_validate(row)

    stored = db.scalar(previous)
    if stored is not None:
        return replay(stored)
    check_position(video, payload.position_ms)
    now = timestamp()
    item = ReviewNote(
        video_id=video_id,
        request_id=str(payload.request_id),
        request_hash=digest,
        body=payload.body,
        position_ms=payload.position_ms,
        category=payload.category.value,
        state="open",
        revision=1,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        stored = db.scalar(previous)
        if stored is None:
            raise
        return replay(stored)
    audit(db, item, "review_note_create")
    result = Note.model_validate(item)
    db.commit()
    return result


def edit(db: Session, video_id: int, note_id: int, payload: EditNote):
    video = get_asset(db, video_id)
    note = db.scalar(
        select(ReviewNote).where(ReviewNote.video_id == video_id, ReviewNote.id == note_id)
    )
    if note is None:
        raise HTTPException(404, "Note not found")
    changes = payload.model_dump(exclude_unset=True, exclude={"revision"}, mode="json")
    if "position_ms" in changes:
        check_position(video, changes["position_ms"])
    before = summary(note)
    result = db.execute(
        update(ReviewNote)
        .where(
            ReviewNote.id == note_id,
            ReviewNote.video_id == video_id,
            ReviewNote.revision == payload.revision,
        )
        .values(**changes, updated_at=timestamp(), revision=ReviewNote.revision + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "This note changed. Refresh and review the latest revision.")
    db.refresh(note)
    audit(db, note, "review_note_edit", before)
    out = Note.model_validate(note)
    db.commit()
    return out


def list_notes(db: Session, video_id: int, state: State | None, page: int, size: int):
    get_asset(db, video_id)
    scope = ReviewNote.video_id == video_id
    counts = dict(
        db.execute(
            select(ReviewNote.state, func.count()).where(scope).group_by(ReviewNote.state)
        ).all()
    )
    stmt = select(ReviewNote).where(scope)
    if state:
        stmt = stmt.where(ReviewNote.state == state.value)
    rows = db.scalars(
        stmt.order_by(ReviewNote.position_ms.asc().nulls_last(), ReviewNote.id.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return NotePage(
        items=[Note.model_validate(row) for row in rows],
        page=page,
        page_size=size,
        total=counts.get(state.value, 0) if state else sum(counts.values()),
        open_count=counts.get("open", 0),
        resolved_count=counts.get("resolved", 0),
    )


def history(db: Session, video_id: int, note_id: int, before: int | None, size: int):
    note = db.scalar(
        select(ReviewNote.id).where(ReviewNote.video_id == video_id, ReviewNote.id == note_id)
    )
    if note is None:
        raise HTTPException(404, "Note not found")
    events = select(AuditLog).where(
        AuditLog.entity_type == "review_note",
        AuditLog.entity_id == note_id,
        AuditLog.action.in_(("review_note_create", "review_note_edit")),
    )
    if before is not None:
        events = events.where(AuditLog.id < before)
    rows = db.scalars(events.order_by(AuditLog.id.desc()).limit(size + 1)).all()
    return NoteHistory(
        items=[
            RevisionEvent(
                id=row.id,
                timestamp=row.created_at.replace(tzinfo=UTC),
                previous=row.before_json,
                current=row.after_json,
            )
            for row in rows[:size]
        ],
        next_before=rows[size - 1].id if len(rows) > size else None,
    )

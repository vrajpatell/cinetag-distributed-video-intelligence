from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.pagination import paginate_sa_query
from app.db.models import GeneratedTag, VideoAsset
from app.db.session import get_db

router = APIRouter()


@router.get("/review")
def list_review_items(
    db: Session = Depends(get_db),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    status: str = "pending_review",
    tag_type: str | None = None,
    source: str | None = None,
    video_id: int | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
):
    q = db.query(GeneratedTag).filter(GeneratedTag.status == status)
    if tag_type:
        q = q.filter(GeneratedTag.tag_type == tag_type)
    if source:
        q = q.filter(GeneratedTag.source == source)
    if video_id is not None:
        q = q.filter(GeneratedTag.video_id == video_id)
    if created_after:
        try:
            dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
            q = q.filter(GeneratedTag.created_at >= dt)
        except ValueError:
            raise HTTPException(400, detail="invalid created_after datetime") from None
    if created_before:
        try:
            dt = datetime.fromisoformat(created_before.replace("Z", "+00:00"))
            q = q.filter(GeneratedTag.created_at <= dt)
        except ValueError:
            raise HTTPException(400, detail="invalid created_before datetime") from None
    q = q.order_by(GeneratedTag.created_at.desc())
    raw = paginate_sa_query(q, page=page, page_size=page_size)
    out = []
    for tag in raw["items"]:
        video = db.get(VideoAsset, tag.video_id)
        out.append(
            {
                "id": tag.id,
                "video_id": tag.video_id,
                "video_title": video.title if video else None,
                "tag_type": tag.tag_type,
                "tag_value": tag.tag_value,
                "confidence": tag.confidence or 0.0,
                "source": tag.source,
                "status": tag.status,
                "rationale": tag.rationale,
                "created_at": tag.created_at.isoformat() if tag.created_at else None,
            }
        )
    return {
        "items": out,
        "page": raw["page"],
        "page_size": raw["page_size"],
        "total": raw["total"],
        "has_next": raw["has_next"],
    }

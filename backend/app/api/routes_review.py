from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import GeneratedTag, VideoAsset
from app.db.session import get_db

router = APIRouter()


@router.get('/review')
def list_review_items(db: Session = Depends(get_db)):
    pending = (
        db.query(GeneratedTag)
        .filter(GeneratedTag.status == 'pending_review')
        .order_by(GeneratedTag.created_at.desc())
        .limit(100)
        .all()
    )
    out = []
    for tag in pending:
        video = db.get(VideoAsset, tag.video_id)
        out.append(
            {
                'id': tag.id,
                'video_id': tag.video_id,
                'video_title': video.title if video else None,
                'tag_type': tag.tag_type,
                'tag_value': tag.tag_value,
                'confidence': tag.confidence or 0.0,
                'source': tag.source,
                'status': tag.status,
                'rationale': tag.rationale,
                'created_at': tag.created_at.isoformat() if tag.created_at else None,
            }
        )
    return out

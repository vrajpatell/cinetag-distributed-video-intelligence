from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import GeneratedTag, AuditLog
from app.observability.metrics import tags_approved, tags_rejected
router=APIRouter()
class TagPatch(BaseModel): status:str|None=None; tag_value:str|None=None
class ManualTag(BaseModel): tag_type:str; tag_value:str; confidence:float=1.0
@router.patch('/tags/{tag_id}')
def patch(tag_id:int,p:TagPatch,db:Session=Depends(get_db)):
    t=db.get(GeneratedTag,tag_id)
    if not t: raise HTTPException(404)
    before={"status":t.status,"tag_value":t.tag_value}
    if p.status: t.status=p.status
    if p.tag_value: t.tag_value=p.tag_value
    if t.status=='approved': tags_approved.inc()
    if t.status=='rejected': tags_rejected.inc()
    db.add(AuditLog(actor='reviewer',action='tag_update',entity_type='tag',entity_id=t.id,before_json=before,after_json={"status":t.status,"tag_value":t.tag_value}))
    db.commit(); return t
@router.post('/videos/{video_id}/tags/manual')
def manual(video_id:int,p:ManualTag,db:Session=Depends(get_db)):
    t=GeneratedTag(video_id=video_id,tag_type=p.tag_type,tag_value=p.tag_value,confidence=p.confidence,source='manual',status='approved')
    db.add(t); db.commit(); db.refresh(t); return t

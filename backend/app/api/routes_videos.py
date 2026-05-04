from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import VideoAsset, FrameSample, SceneSegment, Transcript, GeneratedTag
router=APIRouter(prefix='/videos')
@router.get('')
def list_videos(db:Session=Depends(get_db)): return db.query(VideoAsset).all()
@router.get('/{video_id}')
def get_video(video_id:int, db:Session=Depends(get_db)):
    v=db.get(VideoAsset, video_id)
    if not v: raise HTTPException(404)
    return v
@router.get('/{video_id}/frames')
def frames(video_id:int, db:Session=Depends(get_db)): return db.query(FrameSample).filter_by(video_id=video_id).all()
@router.get('/{video_id}/scenes')
def scenes(video_id:int, db:Session=Depends(get_db)): return db.query(SceneSegment).filter_by(video_id=video_id).all()
@router.get('/{video_id}/transcript')
def transcript(video_id:int, db:Session=Depends(get_db)): return db.query(Transcript).filter_by(video_id=video_id).first()
@router.get('/{video_id}/tags')
def tags(video_id:int, db:Session=Depends(get_db)): return db.query(GeneratedTag).filter_by(video_id=video_id).all()

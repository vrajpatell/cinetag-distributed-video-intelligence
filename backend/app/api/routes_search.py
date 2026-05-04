from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import EmbeddingRecord, VideoAsset
from app.ml.mock_embedding_client import MockEmbeddingClient
router=APIRouter(prefix='/search')
class Query(BaseModel): query:str; tag_type:str|None=None; status:str|None=None; duration_min:float|None=None; duration_max:float|None=None
@router.post('/semantic')
def semantic(q:Query, db:Session=Depends(get_db)):
    target=MockEmbeddingClient().embed(q.query)
    results=[]
    for rec in db.query(EmbeddingRecord).all():
        sim=sum(a*b for a,b in zip(target, rec.embedding))
        v=db.get(VideoAsset, rec.video_id)
        if v: results.append({"video_id":v.id,"title":v.title,"score":sim,"explanation":f"Matched {rec.entity_type}"})
    return sorted(results,key=lambda x:x['score'], reverse=True)[:20]

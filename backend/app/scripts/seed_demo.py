from app.db.session import Base, engine, SessionLocal
from app.db.models import VideoAsset, ProcessingJob, Transcript, GeneratedTag, EmbeddingRecord, FrameSample
from app.ml.mock_embedding_client import MockEmbeddingClient

Base.metadata.create_all(bind=engine)
db = SessionLocal()
video = VideoAsset(title='Demo video', original_filename='demo.mp4', storage_key='videos/demo.mp4', status='completed', duration_seconds=45.0, width=1280, height=720, codec='h264', bitrate=1200000, frame_rate=30.0, file_size_bytes=3000000)
db.add(video); db.commit(); db.refresh(video)
db.add(ProcessingJob(video_id=video.id, status='completed', current_stage='finalize_index'))
db.add(Transcript(video_id=video.id, text='Welcome to CineTag demo.', language='en', confidence=0.99))
db.add(FrameSample(video_id=video.id, timestamp_seconds=3.0, storage_key='frames/1.jpg', description='host speaking'))
db.add(GeneratedTag(video_id=video.id, tag_type='genre', tag_value='documentary', confidence=0.9, status='pending_review'))
emb=MockEmbeddingClient().embed('Welcome to CineTag demo.')
db.add(EmbeddingRecord(video_id=video.id, entity_type='transcript', entity_id=video.id, embedding=emb, text='Welcome to CineTag demo.'))
db.commit(); print('seeded')

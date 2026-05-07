# CineTag AI & Video Processing Capabilities

This document explains the end-to-end intelligence pipeline implemented in this project:

- What AI/ML capabilities exist today
- How a video is uploaded
- What transformations run in the distributed worker pipeline
- What final outputs are produced and where they are surfaced

---

## 1) System capabilities at a glance

CineTag is a distributed video intelligence platform with four major capability layers.

### A. Ingestion and storage capabilities

- Direct-to-object-store upload using signed URLs (`/api/uploads/init` -> `PUT` -> `/api/uploads/complete`)
- Support for `video/mp4`, `video/quicktime`, `video/x-matroska` (plus `application/octet-stream`)
- Upload size guardrails via configurable `max_upload_size_mb`
- Storage backends:
  - GCS (`GCSStore`) for cloud deployment
  - Local filesystem (`LocalStore`) for development, with path traversal protections
- Legacy small-file upload route (`/api/videos/upload`) retained for local/dev workflows

### B. Distributed processing capabilities

- Celery-based asynchronous pipeline workers
- Stage-based pipeline with per-stage execution records and timings
- Retry model with resume-from-stage behavior (`/api/jobs/{job_id}/retry`)
- Idempotent cleanup of generated artifacts during reruns
- Partial completion model when non-strict fallback behavior is used

### C. AI and machine intelligence capabilities

- LLM-powered metadata generation (`llm_tagging`) from transcript + scene/frame context
- Automatic typed tags:
  - `genre`, `mood`, `theme`, `object`, `scene`, `moderation`, `entity`, `language`
- Confidence-scored tags with rationale and source attribution
- Transcript generation (mock or OpenAI Whisper, based on provider config)
- Embedding generation for semantic search and recommendation signals
- Vector similarity search (`/api/search/semantic`) across transcript/tag/scene embeddings

### D. Human-in-the-loop and governance capabilities

- Review queue for AI-generated tags (`/api/review`)
- Approve/reject/edit tag workflow (`PATCH /api/tags/{id}`)
- Manual tag insertion (`POST /api/videos/{id}/tags/manual`)
- Audit trail for tag and publish actions (`audit_logs`)
- Publish gate requiring reviewed tags (`POST /api/videos/{id}/publish`)

---

## 2) End-to-end upload flow

The primary upload flow is designed to avoid proxying large videos through the API.

### Step 1: Upload initialization

Client calls:

`POST /api/uploads/init`

Request includes:

- `filename`
- `content_type`
- `size_bytes`
- optional `title`

Backend behavior:

- Validates content type and max size
- Sanitizes filename and builds a canonical storage key:
  - `originals/{uuid_hex}/{safe_filename}`
- Generates upload URL:
  - GCS signed v4 PUT URL when `storage_backend=gcs`
  - Local direct PUT endpoint in non-GCS mode
- Creates a `video_assets` row with status `upload_pending`

Response includes:

- `video_id`
- `storage_key`
- `upload_url`
- `upload_method` (`PUT`)
- required headers (`Content-Type`)

### Step 2: Binary upload

Client uploads file directly using `XMLHttpRequest` PUT to `upload_url`.

Frontend tracks:

- Percent complete
- Bytes uploaded
- Upload speed
- ETA

### Step 3: Upload completion and job creation

Client calls:

`POST /api/uploads/complete`

Request includes:

- `video_id`
- `storage_key` (must match initialized row)
- optional updated `title`

Backend behavior:

- Verifies video exists and storage key matches
- Verifies uploaded object exists in object store
- Reads metadata (such as size) from storage
- Verifies worker broker connectivity before queueing
- Creates `processing_jobs` row (`queued`) and enqueues `run_pipeline`
- Marks video status as `uploaded`

Idempotency behavior:

- If same upload is completed again and job already exists for an uploaded asset, existing job is returned instead of duplicating work.

---

## 3) Transformation pipeline stages

Pipeline stages are executed in this order:

1. `metadata_extraction`
2. `frame_sampling`
3. `scene_segmentation`
4. `transcription`
5. `llm_tagging`
6. `embedding`
7. `review_ready`
8. `completed`

Each stage writes a `processing_stage_runs` record with status, timing, and errors.

### 3.1 metadata_extraction

How it works:

- Attempts `ffprobe` on local materialized original
- Extracts duration, width, height, codec, bitrate, frame rate
- Writes results to `video_assets`

Fallback behavior:

- If media tools are unavailable and `MEDIA_STRICT=false`, deterministic placeholder metadata is used and stage is marked degraded
- If `MEDIA_STRICT=true`, stage fails

### 3.2 frame_sampling

How it works:

- Samples representative timestamps from video duration
- Uses `ffmpeg` to extract JPEG frames
- Uploads frames to object store:
  - `frames/{video_id}/frame_XXX.jpg`
- Writes `frame_samples` records

Fallback behavior:

- When frame extraction fails and strict mode is off, persists placeholder 1x1 JPEGs

### 3.3 scene_segmentation

How it works:

- Uses ffmpeg scene-change detection (`showinfo` + threshold)
- Builds scene boundaries from detected timestamps
- Falls back to sampled boundaries if no scene-change timestamps detected
- Writes `scene_segments`

### 3.4 transcription

How it works:

- Extracts mono 16kHz MP3 from video via ffmpeg
- Calls `transcribe_audio()` provider abstraction
- Writes `transcripts` row and uploads transcript text to:
  - `transcripts/{video_id}/transcript.txt`

Provider behavior:

- `TRANSCRIPTION_PROVIDER=mock` -> deterministic fallback text
- `TRANSCRIPTION_PROVIDER=openai` -> Whisper API path when audio + API key are available
- Non-strict mode can fall back to mock and mark stage degraded

### 3.5 llm_tagging

How it works:

- Builds prompt context from:
  - video metadata
  - transcript excerpt
  - frame count
  - scene count
- Calls `generate_tag_bundle()` provider abstraction
- Stores:
  - video summary in `video_assets.summary`
  - generated tags in `generated_tags` with:
    - `tag_type`
    - `tag_value`
    - `confidence`
    - `source`
    - `status=pending_review`
    - `rationale`

Tag taxonomy generated:

- `genre`
- `mood`
- `theme`
- `object`
- `scene`
- `moderation`
- `entity`
- `language` (from age suitability mapping)

### 3.6 embedding

How it works:

- Generates embeddings for three entity classes:
  - transcript text
  - generated tags (type + value + rationale text)
  - scene summaries
- Stores vectors and source text in `embedding_records`

### 3.7 review_ready and completed

How it works:

- Video status is moved to `review_ready`
- Tags default to `pending_review` if unset
- Final stage marks job `completed` or `partially_completed`
  - `partially_completed` when one or more stages ran with degraded fallbacks

---

## 4) AI provider architecture and strictness model

The project uses provider abstraction so behavior can switch without route-level code changes.

### Provider toggles

- `LLM_PROVIDER` (`mock` or `openai`)
- `EMBEDDING_PROVIDER` (`mock` or `openai`)
- `TRANSCRIPTION_PROVIDER` (`mock` or `openai`)

### OpenAI-related settings

- `OPENAI_API_KEY`
- `OPENAI_LLM_MODEL` (default `gpt-4o-mini`)
- `OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-small`)
- `OPENAI_TRANSCRIPTION_MODEL` (default `whisper-1`)

### Reliability controls

- `PROVIDER_STRICT=false` (default):
  - Provider failures can fall back to deterministic mock behavior
  - Job can finish as `partially_completed` with degraded reason tracking
- `PROVIDER_STRICT=true`:
  - Provider failures raise hard errors
  - Job fails visibly for operational action

### Media controls

- `MEDIA_STRICT=false` (default):
  - ffmpeg/ffprobe gaps can fall back to placeholders
- `MEDIA_STRICT=true`:
  - media extraction failures fail the pipeline stage

---

## 5) Final outputs produced by the pipeline

A successfully processed video yields the following persistent outputs.

### Database artifacts

- `video_assets`: core asset metadata + AI summary + status
- `processing_jobs`: job-level lifecycle (`queued/running/completed/failed/partially_completed`)
- `processing_stage_runs`: per-stage timeline and errors
- `frame_samples`: sampled frame metadata and storage locations
- `scene_segments`: scene windows with summaries
- `transcripts`: transcript text + language/confidence
- `generated_tags`: AI/manual tags, confidence, status, rationale
- `embedding_records`: vectors for transcript/tag/scene entities
- `audit_logs`: review and publish history

### Object storage artifacts

- Original uploads:
  - `originals/{uuid}/{filename}`
- Frames:
  - `frames/{video_id}/frame_XXX.jpg`
- Transcript file:
  - `transcripts/{video_id}/transcript.txt`

### API-facing outputs

- Video catalog and details:
  - `GET /api/videos`
  - `GET /api/videos/{id}`
- Artifact drill-down:
  - `/api/videos/{id}/frames`
  - `/api/videos/{id}/scenes`
  - `/api/videos/{id}/transcript`
  - `/api/videos/{id}/tags`
- Job observability:
  - `GET /api/jobs`
  - `GET /api/jobs/{id}`
  - `GET /api/jobs/{id}/stages`
- Human review:
  - `GET /api/review`
  - `PATCH /api/tags/{id}`
- Semantic discovery:
  - `POST /api/search/semantic`
- Publish:
  - `POST /api/videos/{id}/publish`

---

## 6) How final results are surfaced in product experience

The frontend consumes the above outputs in dedicated operational/product surfaces:

- Upload page:
  - Signed upload preparation, direct object-store transfer, finalize + job queue
- Jobs page:
  - Live pipeline visibility with status breakdown, stage progression, retries
- Review page:
  - Pending AI tags with approve/reject/edit controls
- Search page:
  - Semantic retrieval with result explanation and matched tags
- Video detail page:
  - AI summary
  - typed tags and confidence
  - processing/job timeline
  - media metadata (duration, codec, bitrate, frame rate, size)
  - publish action once review conditions are met

---

## 7) Publish and “done” definition

Pipeline completion does not automatically publish content.

A video is truly catalog-ready when:

1. Worker pipeline finishes and marks video `review_ready`
2. Human reviewer resolves all `pending_review` tags
3. At least one tag is approved
4. `POST /api/videos/{id}/publish` is executed

Only then does asset status become `published`, and a publish audit entry is recorded.

---

## 8) Notes on current scale profile

- Semantic search currently computes cosine similarity in-memory across `embedding_records`
- This is effective for demo/small catalogs
- For larger catalogs, move embeddings to a vector index service (for example Vertex AI Vector Search or pgvector-backed ANN query architecture)


# CineTag — AI-Powered Video Intelligence Platform

> Cloud-native video intelligence for tagging, discovery, and recommendation-ready metadata — built on GCP.

CineTag is a portfolio-grade demo product that shows how a modern streaming platform can transform raw video assets into searchable, recommendation-ready content using distributed cloud processing and AI-powered metadata generation.

It is **not** a Netflix clone. It is streaming-platform-inspired infrastructure that combines three real engineering problems into one product:

1. **Distributed video processing pipeline** — direct-to-GCS ingestion, autoscaled Celery workers, retryable per-stage tasks.
2. **LLM-based content tagging** — genres, moods, themes, scenes, entities, and moderation labels generated from transcript + frames.
3. **Recommendation-ready discovery** — semantic search, related-content rails, and tag-cluster recommendations.

---

## 1. What this project demonstrates

- A polished **Next.js (App Router)** UI with cinematic streaming-platform styling
- Direct-to-GCS **signed-URL upload** flow that never proxies large files through the API
- A FastAPI **control-plane** with typed routes for uploads, jobs, videos, tags, search, and review
- Distributed pipeline observability: per-job stage timeline, retry counts, and pipeline visualization
- Human-in-the-loop **AI tag review** with audit trail
- **Semantic discovery** experience with explainable matches and filters
- **Production deployment** on Cloud Run with Artifact Registry, Cloud SQL, Memorystore, GCS, and Secret Manager

## 2. Why it matters for streaming platforms

Streaming platforms run high-volume content pipelines that look almost identical to CineTag's:

- An **ingestion plane** that accepts huge files reliably and decouples upload from compute
- A **worker plane** that performs many independent ML/metadata tasks per asset
- A **metadata plane** that produces LLM-grade descriptive metadata for search and recs
- A **discovery plane** that turns metadata into rails, recommendations, and personalization signals

CineTag implements one credible, end-to-end version of each so the architecture is *interview-ready*.

## 3. Architecture

```
       Browser (Next.js · Cloud Run)
              │
   signed PUT │           control-plane API
       to GCS │           ┌───────────────┐
              ▼           │  FastAPI      │
        ┌──────────┐      │  Cloud Run    │
        │   GCS    │◄────►│  /api/uploads │
        │ originals│      │  /api/jobs    │
        └──────────┘      │  /api/videos  │
              │           │  /api/search  │
              ▼           │  /api/review  │
       Worker Pipeline    └───────────────┘
       (Cloud Run worker · Celery)
              │   metadata · frames · scenes
              │   transcripts · LLM tags · embeddings
              ▼
        Cloud SQL (Postgres) ◄──── Memorystore Redis (queue + cache)
              │
              ▼
       Search & recommendations
```

## 4. Demo flow

1. Open the Browse page — it shows a cinematic homepage with rails, metrics, pipeline flow, and architecture cards. (Demo data fills any rail with no live videos yet.)
2. Visit `/upload` and drop in a `.mp4`, `.mov`, or `.mkv`. The browser performs a direct-to-GCS PUT, then the API enqueues a worker job.
3. Visit `/jobs` to watch the operations dashboard. Stage badges, retries, and timing all update live.
4. Visit `/review` to approve, reject, or edit AI-generated tags.
5. Visit `/search` for natural-language semantic discovery.
6. Click any video to open `/videos/[id]` — a strong technical/product page with metadata, AI summary, tag cloud grouped by type, processing job timeline, and related-content rails.

## 5. GCP services used

| Service                  | Role                                                          |
|--------------------------|---------------------------------------------------------------|
| Cloud Run (API)          | FastAPI control plane, signed URLs                            |
| Cloud Run (Worker)       | Celery worker pipeline, autoscaled by load                    |
| Cloud Run (Frontend)     | Next.js standalone runtime, port 8080                         |
| Cloud SQL (Postgres)     | Assets, jobs, tags, embeddings, audit logs                    |
| Memorystore (Redis)      | Celery broker / result backend, cache                         |
| Google Cloud Storage     | Original videos, frames, transcripts, thumbnails              |
| Artifact Registry        | Container images for API / worker / frontend                  |
| Secret Manager           | Database password, LLM keys, signed-URL credentials           |
| Cloud Monitoring/Logging | Metrics, traces, latency SLOs, alerts                         |
| Cloud Build / Cloud Deploy | CI/CD for API, worker, and frontend images                  |
| Vertex AI Vector Search (or AlloyDB w/ `pgvector`) | Production vector store to replace the in-memory cosine scan in `/api/search/semantic` |
| Vertex AI Gemini API     | First-party alternative to the OpenAI LLM provider for tag generation |
| Vertex AI Embeddings     | First-party alternative to OpenAI embeddings (`text-embedding-005`)   |
| Speech-to-Text v2        | First-party alternative to Whisper for the `transcription` stage      |
| Video Intelligence API   | Optional substitute for ffmpeg-based scene detection / object tagging |
| Cloud Tasks / Pub/Sub    | Production replacement for Redis-backed Celery if you need GCP-native queueing |
| Cloud Workflows or Eventarc | Orchestrate the upload → process → publish pipeline as managed workflow steps |

## 6. Upload architecture

Large video uploads use a **direct-to-GCS signed PUT**:

```
POST /api/uploads/init       -> { upload_url, video_id, storage_key, ... }
PUT  <signed GCS URL>        -> binary file body, with progress events
POST /api/uploads/complete   -> { video_id, job_id, status: "queued" }
```

Why this design:

- The API never has to buffer multi-GB videos.
- The browser gets reliable upload progress through `XMLHttpRequest`.
- Worker autoscaling can be tuned independently of API replicas.
- Orphaned uploads (`upload_pending` status) can be GC'd by a GCS lifecycle rule.

The legacy `/api/videos/upload` endpoint stays for tiny dev uploads and returns **413** for anything larger, with a message pointing clients to the signed-URL flow.

For local development, when `STORAGE_BACKEND != gcs`, the API issues a pseudo-signed URL pointing at its own `PUT /api/uploads/direct/{key}` route so the same client code works end-to-end without GCS.

## 7. LLM tagging architecture

Each video flows through a Celery pipeline of independently retryable stages:

`metadata_extraction → frame_sampling → scene_segmentation → transcription → llm_tagging → embedding → review_ready → completed`

- **Visual frames** + **scene boundaries** + **transcript** are fed to the LLM tagging service.
- The LLM returns typed tags: `genre`, `mood`, `object`, `scene`, `theme`, `moderation`, `entity`.
- Each tag carries a confidence score, source (`llm | transcript | visual_frame | metadata | manual`), and rationale.
- Tags land in a **review queue** at `pending_review`. Humans approve, reject, or edit; every decision is recorded in `audit_logs`.

Mock providers (`MockLLMClient`, `MockEmbeddingClient`) keep the project deterministic and free to demo. The pipeline can switch to real providers via environment variables — no code changes:

| Env var                       | Default                  | Purpose                                                                 |
|-------------------------------|--------------------------|-------------------------------------------------------------------------|
| `LLM_PROVIDER`                | `mock`                   | `mock` or `openai` — controls tag generation in `llm_tagging`           |
| `EMBEDDING_PROVIDER`          | `mock`                   | `mock` or `openai` — used by both the worker AND `/api/search/semantic` |
| `TRANSCRIPTION_PROVIDER`      | `mock`                   | `mock` or `openai` (Whisper) — used in `transcription`                  |
| `OPENAI_API_KEY`              | _unset_                  | Required when any provider is `openai`                                  |
| `OPENAI_LLM_MODEL`            | `gpt-4o-mini`            | Model used for tag generation                                           |
| `OPENAI_EMBEDDING_MODEL`      | `text-embedding-3-small` | Model used for query + corpus embeddings                                |
| `OPENAI_TRANSCRIPTION_MODEL`  | `whisper-1`              | Model used for STT                                                      |
| `PROVIDER_STRICT`             | `false`                  | If `true`, OpenAI failures raise instead of silently using mock output  |
| `MEDIA_STRICT`                | `false`                  | If `true`, ffmpeg/ffprobe/audio-extraction failures fail the stage      |
| `SCENE_DETECTION_THRESHOLD`   | `0.35`                   | Sensitivity threshold for ffmpeg scene detection                        |

When `PROVIDER_STRICT` is off (the default), an OpenAI outage is logged and the pipeline falls back to deterministic mock output so demos never break — but the job is then marked `partially_completed` and the degraded stages are listed in `error_message` so operators can see exactly what fell back. When `PROVIDER_STRICT=true`, the same outage fails the job instead, making it visible to alerting.

> Search and the worker share the same embedding provider. If `EMBEDDING_PROVIDER` is changed mid-flight, existing embeddings keep their old vector dimensionality; `/api/search/semantic` skips dim-mismatched records rather than zero-scoring the catalog. Re-run the pipeline (or backfill embeddings) when migrating between providers.

## 8. Recommendation-ready discovery

- **Semantic search** ranks results by cosine similarity against query embeddings, scoped by tag-type and confidence filters. Both the corpus embeddings and query embeddings go through the same provider abstraction, so swapping `EMBEDDING_PROVIDER` between `mock` and `openai` keeps search consistent with the pipeline.
- **Related content rails** combine tag-cluster overlap with embedding similarity.
- **Recommendation reason** strings are surfaced in the UI ("Because of these tags") so the experience is explainable, not a black box.
- **Today** the search route does an in-memory cosine scan over `embedding_records` — fine for the demo dataset but not for a large catalog. The natural production upgrade is **Vertex AI Vector Search** or **AlloyDB / Cloud SQL with the `pgvector` extension** so the same embeddings can be queried with sub-second ANN.

### Publish lifecycle

The pipeline only ever brings a video to `review_ready`. Going live is an explicit human action:

1. The pipeline marks the video `review_ready` and tags `pending_review`.
2. Reviewers approve / reject / edit each tag in `/review`. Every decision is written to `audit_logs`.
3. Once **all** auto-generated tags are resolved (no `pending_review` left) and **at least one** is approved, `POST /api/videos/{id}/publish` flips the video to `status=published` and writes a `video_publish` audit row. The video detail page exposes this as a "Publish video" button.

## 9. Local development

```bash
cp .env.example .env
make up                     # postgres + redis + minio + api + worker via docker-compose
make seed                   # optional: demo data

# Frontend
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

- API: <http://localhost:8000/docs>
- Frontend: <http://localhost:3000>
- Health: `curl http://localhost:8000/health`

The frontend uses **only** `NEXT_PUBLIC_API_BASE_URL` to talk to the API — no relative `/api/...` calls in the browser.

## 10. GCP deployment

Build and push images via Cloud Build (`cloudbuild.yaml`) and deploy three Cloud Run services: `cinetag-api`, `cinetag-worker`, `cinetag-frontend`.

Frontend image build args:

```
--build-arg NEXT_PUBLIC_API_BASE_URL=https://cinetag-api-...run.app
--build-arg NEXT_PUBLIC_APP_ENV=gcp
--build-arg NEXT_PUBLIC_BUILD_VERSION=$SHORT_SHA
--build-arg NEXT_PUBLIC_GCP_REGION=us-central1
```

Critical IAM:

- The API service account needs `roles/iam.serviceAccountTokenCreator` to sign GCS URLs.
- The bucket must allow `PUT` from the frontend origin via a CORS rule.

See `docs/deploy-gcp-cloud-run.md` for full Terraform + gcloud steps.

### Production hardening updates

- Semantic search now supports Cloud SQL `pgvector` with a guarded Python fallback.
- Upload and retry routes publish jobs through a queue abstraction (`celery` or `pubsub`).
- Terraform now provisions dedicated VPC networking for private Cloud SQL and private Redis.
- Pub/Sub topic/subscription and IAM wiring are available for GCP-native dispatch.

### Verification

```bash
curl $API_URL/health
curl $API_URL/ready
curl $API_URL/api/videos
curl -X POST $API_URL/api/uploads/init \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.mp4","content_type":"video/mp4","size_bytes":12345,"title":"test"}'
gcloud storage ls gs://cinetag-distributed-video-media/originals/
gcloud run services logs read cinetag-worker --region us-central1 --limit 100
```

## 11. Screenshots

> _Add screenshots of the homepage, upload, jobs dashboard, review queue, search, and video detail page here._

```
frontend/docs/screenshots/
  home.png
  upload.png
  jobs.png
  review.png
  search.png
  video-detail.png
```

## 12. Resume bullet

> Built **CineTag**, a cloud-native video intelligence platform on GCP that ingests video assets, processes them through distributed workers, generates LLM-powered metadata, and powers semantic discovery and recommendation-ready content workflows using Next.js, FastAPI, Cloud Run, Cloud SQL, Redis, and Google Cloud Storage.

---

## Branding note

CineTag uses an original cinematic dark theme with a red accent. It does **not** use Netflix logos, wordmarks, or copyrighted assets. It is "streaming-platform inspired" and CineTag-branded only.

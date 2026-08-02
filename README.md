# CineTag — AI-Powered Video Intelligence Platform

> Local-first video intelligence using open-source models and infrastructure, with no required cloud account or metered AI API.

---

## Table of contents

1. [What this project is](#1-what-this-project-is)
2. [What the platform does](#2-what-the-platform-does)
3. [Why CineTag exists and who it helps](#3-why-cinetag-exists-and-who-it-helps)
4. [Architecture at a glance](#4-architecture-at-a-glance)
5. [End-to-end user and operator flow](#5-end-to-end-user-and-operator-flow)
6. [Technology stack](#6-technology-stack)
7. [Processing pipeline](#7-processing-pipeline)
8. [Upload design](#8-upload-design)
9. [AI tagging and providers](#9-ai-tagging-and-providers)
10. [Semantic search and embeddings](#10-semantic-search-and-embeddings)
11. [Queues, workers, and dispatch](#11-queues-workers-and-dispatch)
12. [Review, publish, and governance](#12-review-publish-and-governance)
13. [Infrastructure options](#13-infrastructure-options)
14. [Observability](#14-observability)
15. [Local development](#15-local-development)
16. [Deployment options](#16-deployment-options)
17. [Configuration reference](#17-configuration-reference)
18. [Documentation map](#18-documentation-map)
19. [Limitations and natural extensions](#19-limitations-and-natural-extensions)
20. [Screenshots](#20-screenshots)
21. [Resume bullet](#21-resume-bullet)
22. [Branding note](#22-branding-note)

---

## 1. What this project is

**CineTag** is a full-stack, production-oriented **video intelligence platform**: it ingests video assets, runs them through a **staged asynchronous pipeline**, generates **AI-assisted metadata** (tags, transcripts, embeddings, sampled frames and scenes), supports **human review** of machine-generated labels, and exposes **semantic search** and **recommendation-oriented** discovery in the UI.

It is intentionally **not** a Netflix-style playback product. There is no adaptive HLS player or DRM stack as a first-class feature; the focus is **metadata extraction, quality control, searchability, and the control-plane patterns** that real streaming and media catalogs depend on.

The codebase is suitable as:

- A **portfolio-grade reference** for how to wire Next.js, FastAPI, local object storage, PostgreSQL, workers, and open-source ML into one coherent product.
- A **teaching artifact** for ingestion → queue → worker stages → persistence → API → UI loops.
- A **starting point** for teams that want to experiment with local LLM tagging, offline transcription, semantic search, or distributed workers without building everything from scratch.

---

## 2. What the platform does

The platform combines four capability layers that mirror how large catalogs are operated in practice.

### Ingestion and storage

- **Local path:** browser upload to a shared filesystem volume; optional cloud mode uses browser-initiated signed URLs to GCS so the API does not buffer large files.
- **Validation:** content types, maximum size, safe filenames, reserved `VideoAsset` rows, and post-upload object existence checks.
- **Legacy path:** small dev uploads via a legacy route (with size limits and guidance toward signed URLs for real files).

### Distributed processing

- **Celery-style** staged pipeline with **per-stage** execution records, timings, retries, and a **partial completion** model when providers or media tooling degrade (configurable strictness).
- Stages include metadata extraction, frame sampling, scene segmentation, transcription, LLM tagging, embedding generation, and completion handoff toward review.
- **ffmpeg/ffprobe** integration where available, with deterministic placeholder behavior when media tools are missing (unless strict media mode is enabled).

### AI and discovery

- **LLM tagging** from transcript + visual/scene context: typed tags (e.g. genre, mood, theme, object, scene, moderation, entity) with confidence, rationale, and source attribution.
- **Transcription** with local faster-whisper by default, plus deterministic mock and optional external providers.
- **Embeddings** for semantic search and related-content signals; search supports **pgvector** (cosine) when enabled and falls back to a **Python cosine** path for local or compatibility scenarios.
- UI surfaces **semantic search**, **related rails**, and **explainable** match reasons where applicable.

### Human-in-the-loop and publishing

- **Review queue** for `pending_review` tags: approve, reject, edit, and add **manual** approved tags.
- **Audit logging** for tag and publish actions.
- **Publish gate:** a video moves to a published state only after pending tags are resolved and at least one approved tag exists (enforced by the API).

---

## 3. Why CineTag exists and who it helps

### For product and catalog owners

Modern libraries need **consistent, searchable metadata** at scale. Manual tagging does not scale; fully automated tagging is rarely trusted without review. CineTag shows a **practical middle path**: AI proposes tags, humans curate, and only then does content surface as “published” for downstream use (search, recommendations, compliance, merchandising).

### For engineers and architects

Streaming and media platforms repeatedly solve the same cross-cutting problems:

| Plane | Problem | How CineTag illustrates it |
|-------|---------|----------------------------|
| Ingestion | Large files, unreliable networks | Signed PUT to object storage; API only orchestrates |
| Compute | Many independent tasks per asset | Staged worker pipeline with retries and observability |
| Metadata | LLM outputs need structure and QC | Typed tags, review queue, audit trail, publish gate |
| Discovery | Text + vector search over catalogs | Semantic API + UI; pgvector path for scale |
| Operations | Secure cloud deployment | Terraform-oriented GCP layout, private DB paths, metrics |

CineTag is **interview- and design-review-ready**: it names real services, real failure modes (strict vs fallback providers), and real tradeoffs (e.g. embedding dimension alignment with the database vector column).

### For learners

The repository ties together **frontend progress UX** (XHR upload with speed and ETA), **backend orchestration**, **relational modeling** (assets, jobs, stages, tags, embeddings, audits), and **cloud deployment** in one repo with tests and docs.

---

## 4. Architecture at a glance

```
       Browser (Next.js)
              |
              v
       FastAPI control plane <----> PostgreSQL + pgvector
              |                         |
              v                         |
       Celery + Valkey queue            |
              |                         |
              v                         |
       Local worker --------------------+
       FFmpeg + faster-whisper + Ollama
              |
              v
       Shared local media volume
```

The default topology runs entirely through Docker Compose. GCP storage, Pub/Sub, Cloud Run, and Vercel remain optional deployment adapters. See [Queues, workers, and dispatch](#11-queues-workers-and-dispatch).

---

## 5. End-to-end user and operator flow

1. **Browse** — Homepage with rails, metrics, pipeline overview, and architecture-oriented cards (demo data can backfill rails when the catalog is empty).
2. **Upload** — `/upload`: drop `.mp4`, `.mov`, or `.mkv`; the client uses **XMLHttpRequest** for progress (percent, bytes, speed, ETA) and stage labels (e.g. preparing signed upload, uploading to object storage, queued for analysis).
3. **Jobs** — `/jobs`: operations-style view of jobs, stage badges, retries, and timing.
4. **Review** — `/review`: approve, reject, or edit AI-generated tags; optional manual tags.
5. **Search** — `/search`: natural-language **semantic** discovery with filters where implemented.
6. **Video detail** — `/videos/[id]`: metadata, AI-oriented summary, tag cloud by type, processing timeline, related content, and publish action when policy allows.

Operators verify deployments with health and readiness probes, logs, and Prometheus metrics (see [Observability](#14-observability)).

---

## 6. Technology stack

| Area | Choices |
|------|---------|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic Settings |
| Workers | Celery with Valkey; optional Pub/Sub adapter |
| Data | PostgreSQL 16 with pgvector, Valkey |
| Objects | Shared local filesystem; optional GCS adapter |
| AI | Ollama + Qwen2 for structured tags, Granite Vision for frames, faster-whisper for STT, `all-minilm` embeddings |
| Media | FFmpeg and ffprobe for metadata, frames, audio, scenes, and previews |
| Search DB | **pgvector** (HNSW-style indexing in migrations) + Python fallback |
| Metrics | Prometheus client counters/histograms on API hot paths |
| Tracing | Optional OpenTelemetry hooks when enabled |
| Packaging / ops | Docker Compose locally; optional Vercel frontend and Terraform/GCP deployment |

---

## 7. Processing pipeline

Stages (conceptual order):

```text
metadata_extraction
  → frame_sampling
  → scene_segmentation
  → transcription
  → llm_tagging
  → embedding
  → review_ready
  → completed
```

Each stage is logged and persisted; failures and fallbacks can surface as **partially completed** jobs with degraded stage metadata for operators. Retries can resume from an appropriate stage depending on job APIs and cleanup behavior.

For a **deeper narrative** of capabilities and edge cases, see [`docs/ai-video-capabilities-and-processing-flow.md`](docs/ai-video-capabilities-and-processing-flow.md).

---

## 8. Upload design

Large uploads use a **direct signed PUT** flow:

```text
POST /api/uploads/init       → { upload_url, video_id, storage_key, ... }
PUT  <signed URL or dev equivalent>   → raw bytes, with client-side progress
POST /api/uploads/complete → validates object, creates ProcessingJob, publishes to queue
```

**Why this design**

- The API avoids holding huge payloads in memory or on disk.
- Upload throughput scales with object storage, not API CPU.
- Worker autoscaling can be tuned independently from API replicas.
- Orphaned `upload_pending` objects can be bounded with **GCS lifecycle** rules.

For local development, when `STORAGE_BACKEND` is not GCS, the API can expose a **direct PUT** URL on the API itself so the same client code runs without a GCP bucket.

The legacy `/api/videos/upload` route remains for tiny files and returns **413** for oversized payloads with guidance to use the signed-URL flow.

---

## 9. AI tagging and providers

The LLM stage consumes **visual frames**, **scene boundaries**, and **transcript** context, and produces **typed** tags with confidence, source (`llm`, `transcript`, `visual_frame`, `metadata`, `manual`), and rationale.

| Env var | Default | Purpose |
|---------|---------|---------|
| `LLM_PROVIDER` | Compose: `ollama` | Local structured tag generation; `mock` is the lightweight fallback |
| `EMBEDDING_PROVIDER` | Compose: `ollama` | Shared local embeddings for workers and semantic search |
| `TRANSCRIPTION_PROVIDER` | Compose: `faster_whisper` | Offline speech-to-text |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Local Ollama server |
| `OLLAMA_LLM_MODEL` | `qwen2:1.5b` | Permissively licensed, low-memory tag model |
| `OLLAMA_EMBEDDING_MODEL` | `all-minilm` | Lightweight 384-dimensional embeddings |
| `OLLAMA_VISION_MODEL` | `granite3.2-vision:2b` | Apache-licensed descriptions of sampled frames |
| `FASTER_WHISPER_MODEL` | `small` | Offline Whisper model; use `base` on lower-memory machines |
| `PROVIDER_STRICT` | `false` | If `true`, provider failures fail the job instead of controlled fallback |
| `MEDIA_STRICT` | `false` | If `true`, ffmpeg/ffprobe failures fail stages instead of placeholders |
| `SCENE_DETECTION_THRESHOLD` | `0.35` | Scene detection sensitivity |

With `PROVIDER_STRICT=false`, missing local models can fall back to deterministic mock behavior. With `PROVIDER_STRICT=true`, inference failures stop the job. Paid OpenAI support remains an optional extra and is not installed or configured by the local stack.

**Search and embeddings must stay consistent:** changing `EMBEDDING_PROVIDER` or model mid-catalog can change vector dimensionality. The API skips dimension mismatches rather than silently corrupting scores; plan **re-embedding** or migrations when switching models.

---

## 10. Semantic search and embeddings

- **`/api/search/semantic`** embeds the query with the same embedding abstraction as the corpus, then ranks by **cosine similarity**.
- **Filters** can include tag type, asset status, and duration bounds (as implemented in the current API).
- **Backends:** when pgvector is enabled and the deployment uses compatible columns and indexes, the route uses **database-side** cosine distance; otherwise it can use a **Python cosine** fallback (useful locally or when the extension is unavailable).
- **Metrics:** search request counts and latency histograms support SLO-style monitoring.

**Operational note:** migrations may define a fixed vector width (e.g. aligned to OpenAI `text-embedding-3-small` output). **Mock embeddings** may use a different dimension and remain in JSON-only storage; those rows may not participate in the pgvector path until dimensions match—plan provider consistency or a dedicated migration strategy for mixed-dimension catalogs.

---

## 11. Queues, workers, and dispatch

The API publishes work via:

```python
publish_processing_job(job_id)
```

| `QUEUE_BACKEND` | Behavior |
|-----------------|----------|
| `celery` / `redis` | Celery task `run_pipeline.delay(job_id)` via Redis broker |
| `pubsub` | JSON event to Google Pub/Sub (`processing_job.created` style payload with `job_id`) |

The **Cloud Run worker** entrypoint is **`python -m app.workers.worker_service_main`**: a small **FastAPI + Uvicorn** process exposes **`/health`** and **`/ready`** on `PORT` for platform probes, and spawns a subprocess:

- **`pubsub`** → `python -m app.workers.pubsub_consumer` (pull, handle, ack/nack)
- **`celery` / `redis`** → `python -m app.workers.worker_main`

So you do **not** need a separate container command for Pub/Sub: set env vars and `QUEUE_BACKEND=pubsub` on the worker service.

Queue publish success and failure are counted in metrics for alerting.

---

## 12. Review, publish, and governance

| Feature | Behavior |
|---------|----------|
| Review queue | Lists pending AI tags (with video context, confidence, rationale, timestamps) |
| Tag updates | Approve, reject, or edit via tag APIs |
| Manual tags | Add human-approved tags where supported |
| Audit log | Rows for tag changes and publish events |
| Publish | `POST /api/videos/{id}/publish` only when **no** tags remain `pending_review` and **at least one** approved tag exists |

The pipeline intentionally lands assets in **`review_ready`**; publishing is a **conscious** product and compliance step.

---

## 13. Infrastructure options

### Local open-source default

Docker Compose runs PostgreSQL/pgvector, Valkey, Ollama, FastAPI, the Celery worker, and Next.js. Originals and derived media share a persistent local volume, while model caches persist across restarts. No cloud account or API key is required. See [`docs/open-source-local-stack.md`](docs/open-source-local-stack.md).

### Optional GCP production path

Terraform and docs cover a **stronger** production layout than “everything on the default VPC”:

- **Dedicated VPC**, subnets, **private service access**, and **VPC peering** for managed services where applicable.
- **Cloud SQL for PostgreSQL** with **private IP**, backups, configurable tier, and deletion protection flags.
- **Memorystore Redis** attached to the same VPC model (not ad-hoc default networking).
- **Pub/Sub** topics (including DLQ patterns where configured), subscriptions, delivery policies, and IAM for API publisher and worker subscriber roles.
- **Cloud Run** for API, worker, and frontend; **Serverless VPC Access** connector for private reachability to SQL and Redis.
- **GCS** for media; **Secret Manager** for credentials; **Artifact Registry** for images.

Exact resource names and apply order are in [`docs/deploy-gcp-cloud-run.md`](docs/deploy-gcp-cloud-run.md). **Brownfield** projects may need imports or state alignment when resources already exist.

---

## 14. Observability

Prometheus-oriented metrics include (non-exhaustive): job totals and failures, **per-stage duration**, videos processed, tags generated and approved/rejected, **queue publish** outcomes, **semantic search** volume and latency, and **Pub/Sub** ack/nack totals.

Optional **OpenTelemetry** instrumentation for FastAPI and SQLAlchemy can be enabled when `OTEL_ENABLED=true` (see application configuration).

---

## 15. Local development

```bash
cp .env.example .env
make up                     # pgvector + Valkey + Ollama + API + worker + frontend
make models                 # pull Qwen2, all-minilm, and Granite Vision into Ollama
make migrate                # create/update the PostgreSQL schema
make seed                   # optional: demo data
```

- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`
- Health: `curl http://localhost:8000/health`

The browser talks to the API **only** through **`NEXT_PUBLIC_API_BASE_URL`** (no silent same-origin `/api` proxy assumption).

Run backend tests and lint (from `backend/`):

```bash
python -m pytest
python -m ruff check .
```

Database schema migrations use **Alembic**; see `backend/alembic/` and scripts referenced in deploy docs.

---

## 16. Deployment options

### Zero-bill local deployment (default)

Run the complete stack on hardware you already own using Docker Compose and the instructions in [`docs/open-source-local-stack.md`](docs/open-source-local-stack.md). This path uses no metered AI API and requires no Vercel or GCP account. Hardware, power, bandwidth, and public hosting are not inherently free.

### Optional Vercel frontend

The checked-in Vercel configuration deploys a free **showcase mode** with **`frontend` as the Root Directory**. Browse, Jobs, Review, Search, and video-detail screens use bundled demo data; uploads and inference are visibly disabled because the persistent Ollama/FFmpeg/Celery stack is not compatible with request-scoped Vercel Functions. No database, model API key, or paid integration is required for the showcase.

To connect a separately hosted backend, set `NEXT_PUBLIC_DEMO_MODE=false` and `NEXT_PUBLIC_API_BASE_URL` to the public HTTPS FastAPI origin. Vercel builds the Next.js app with `npm ci` and `npm run build` and creates Git-based previews.

The backend supports `CORS_ALLOWED_ORIGIN_REGEX` for project-scoped Vercel preview URLs. GCS must separately allow browser `PUT` requests from the production and preview frontend origins. Do not store credentials in `NEXT_PUBLIC_*` variables because those values are shipped to the browser.

See [`docs/deploy-vercel.md`](docs/deploy-vercel.md) for the project settings, environment variables, CORS pattern, topology, and smoke-test checklist.

### Optional GCP API, worker, and data tier

### Production readiness (summary)

- **Database:** Prefer `CLOUD_SQL_CONNECTION_NAME` + `DATABASE_PASSWORD` (Secret Manager) with `APP_ENV=gcp` instead of a Docker-style `DATABASE_URL`.
- **Auth:** Set `AUTH_ENABLED=true` and configure `ADMIN_API_KEY` / `REVIEWER_API_KEY` / `SERVICE_API_KEY`; send `X-API-Key` on mutations. Local Docker defaults to `AUTH_ENABLED=false`.
- **Search:** `SEMANTIC_SEARCH_BACKEND=auto` uses pgvector when dimensions match `embedding_vector_dimension`; otherwise Python JSON search. Use `python -m app.scripts.backfill_embedding_vectors` to populate `embedding_vector` from historical JSON.
- **Docs:** See [`docs/latest-gap-fix-summary.md`](docs/latest-gap-fix-summary.md) and [`docs/streaming-roadmap.md`](docs/streaming-roadmap.md).

### Automated (GitHub Actions → GCP)

Every push to `main` triggers the [`deploy-gcp`](.github/workflows/deploy-gcp.yml) workflow, which lints + tests, builds all three images via Cloud Build (tagging with both `:latest` and `:sha-<commit>`), runs the `cinetag-migrate` Cloud Run job, deploys the new image to `cinetag-api` / `cinetag-worker` / `cinetag-frontend` in parallel, and smoke-tests `/health`. Authentication uses **Workload Identity Federation** — no JSON keys are stored in GitHub.

One-time setup (deployer service account, WIF pool/provider, GitHub secrets/vars) is documented step-by-step in [`docs/cicd-github-actions-gcp.md`](docs/cicd-github-actions-gcp.md).

### Manual

Build and push images (e.g. Cloud Build `cloudbuild.yaml`) and deploy three Cloud Run services: **`cinetag-api`**, **`cinetag-worker`**, **`cinetag-frontend`**.

**Critical:** `NEXT_PUBLIC_*` variables are **inlined at build time** in Next.js. The frontend image **must** receive the public API URL as a **build arg**, for example:

```bash
--build-arg NEXT_PUBLIC_API_BASE_URL=https://<your-api-host>.run.app
--build-arg NEXT_PUBLIC_APP_ENV=gcp
--build-arg NEXT_PUBLIC_BUILD_VERSION=$SHORT_SHA
--build-arg NEXT_PUBLIC_GCP_REGION=us-central1
```

**IAM**

- The API service account typically needs permission to **sign URLs** for your GCS bucket (e.g. `roles/iam.serviceAccountTokenCreator` where applicable to your signing pattern).
- Bucket **CORS** must allow browser `PUT` from your frontend origin.

**Migration / rollback hints** (see deploy doc for detail):

- Keep `QUEUE_BACKEND=celery` until Redis and workers are verified; switch to `pubsub` when topics, subscriptions, and IAM are ready—the **same** worker entrypoint supports both.
- `SEMANTIC_SEARCH_BACKEND=python` forces the pure-Python search path if you need to bypass pgvector during incidents.

```bash
curl $API_URL/health
curl $API_URL/ready
curl $API_URL/api/videos
curl -X POST $API_URL/api/uploads/init \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d '{"filename":"test.mp4","content_type":"video/mp4","size_bytes":12345,"title":"test"}'
gcloud storage ls gs://<your-media-bucket>/originals/
gcloud run services logs read cinetag-worker --region us-central1 --limit 100
```

---

## 17. Configuration reference

Beyond the tables above, important settings include:

- `QUEUE_BACKEND`, `REDIS_URL`, broker/result URLs for Celery modes
- `OLLAMA_BASE_URL`, `OLLAMA_LLM_MODEL`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_VISION_MODEL`
- `FASTER_WHISPER_MODEL`, `FASTER_WHISPER_DEVICE`, `FASTER_WHISPER_COMPUTE_TYPE`
- `PUBSUB_TOPIC_NAME`, `PUBSUB_SUBSCRIPTION_NAME` for Pub/Sub mode
- `STORAGE_BACKEND`, `GCS_BUCKET_NAME`, upload size limits
- `SEMANTIC_SEARCH_BACKEND`, `PGVECTOR_ENABLED`, embedding dimension settings aligned with migrations
- `CORS_ALLOWED_ORIGINS` and optional `CORS_ALLOWED_ORIGIN_REGEX` for browser access to the API
- `SECRET_MANAGER_ENABLED`, Cloud SQL connection env vars for GCP

Authoritative defaults and types live in `backend/app/core/config.py`.

---

## 18. Documentation map

| Document | Contents |
|----------|----------|
| [`docs/open-source-local-stack.md`](docs/open-source-local-stack.md) | Zero-bill local stack, models, hardware profiles, setup, and licensing notes |
| [`docs/deploy-vercel.md`](docs/deploy-vercel.md) | Vercel frontend + GCP backend topology, project settings, environment variables, CORS, verification |
| [`docs/deploy-gcp-cloud-run.md`](docs/deploy-gcp-cloud-run.md) | Terraform, Cloud Run, migration order, rollback |
| [`docs/cicd-github-actions-gcp.md`](docs/cicd-github-actions-gcp.md) | Step-by-step GitHub Actions → GCP CI/CD setup (Workload Identity Federation) |
| [`docs/ai-video-capabilities-and-processing-flow.md`](docs/ai-video-capabilities-and-processing-flow.md) | Deep dive on AI stages, upload, storage, APIs |
| [`docs/production-hardening-plan.md`](docs/production-hardening-plan.md) | Production-hardening scope and checklist |
| [`docs/gcp-architecture.md`](docs/gcp-architecture.md) | GCP architecture narrative |
| [`docs/gcp-security.md`](docs/gcp-security.md) | Security considerations for deployment |
| [`docs/gcp-observability.md`](docs/gcp-observability.md) | Logging, metrics, tracing notes |
| [`docs/gcp-scaling-notes.md`](docs/gcp-scaling-notes.md) | Scaling workers, API, and data tiers |
| [`docs/future-gcp-queue-options.md`](docs/future-gcp-queue-options.md) | Queue and eventing alternatives |
| [`docs/system-design.md`](docs/system-design.md) | System design summary |
| [`docs/interview-talking-points.md`](docs/interview-talking-points.md) | Concise talking points for interviews |
| [`docs/resume-bullets.md`](docs/resume-bullets.md) | Additional resume phrasing |
| [`docs/deploy-render.md`](docs/deploy-render.md) | Render.com deployment path |
| [`docs/deploy-gcp.md`](docs/deploy-gcp.md) | Broader GCP deployment notes |
| [`docs/ui-framework-upgrade-react-nextjs.md`](docs/ui-framework-upgrade-react-nextjs.md) | Frontend stack upgrade notes |

---

## 19. Limitations and natural extensions

CineTag is a **focused** reference, not a full commercial MAM or streaming stack:

- **Playback:** no first-class adaptive streaming or studio DRM in this repo; the value is metadata and control-plane patterns.
- **Vector dimension:** DB column width may be fixed by migration; mixed mock/production dimensions need an operational strategy.
- **Hardware:** local inference is limited by available RAM, VRAM, CPU/GPU speed, disk, and power.
- **Kubernetes / Temporal:** not required for the included design; Docker Compose + Celery/Valkey is the default path.
- **Vertex AI / Video Intelligence API:** reasonable production upgrades, documented as directions rather than the default code path in many environments.
- **Terraform:** greenfield `apply` is smooth; existing GCP projects may hit **already exists** conflicts until state/imports are reconciled.

These boundaries are useful talking points: they show what was **in scope** for a coherent demo product versus what a mature enterprise would add next.

---

## 20. Screenshots

> Add screenshots of the homepage, upload, jobs dashboard, review queue, search, and video detail page.

Suggested paths:

```text
frontend/docs/screenshots/
  home.png
  upload.png
  jobs.png
  review.png
  search.png
  video-detail.png
```

---

## 21. Resume bullet

> Built **CineTag**, a local-first video intelligence platform using Next.js, FastAPI, PostgreSQL/pgvector, Celery/Valkey, FFmpeg, Ollama with Qwen2 and Granite Vision, and faster-whisper; it processes uploaded video into visual descriptions, transcripts, structured tags, embeddings, review workflows, and semantic discovery without requiring paid AI APIs.

---

## 22. Branding note

CineTag uses an original cinematic dark theme with a red accent. It does **not** use Netflix logos, wordmarks, or copyrighted assets. It is **streaming-platform inspired** and CineTag-branded only.

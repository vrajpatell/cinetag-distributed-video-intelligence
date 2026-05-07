# Deploy CineTag on Render

This document provides a pragmatic Render deployment approach for CineTag when GCP is not required.

## 1) Recommended service layout

Create separate Render services for:

- **API** (`backend/Dockerfile`)
- **Worker** (`backend/Dockerfile`, command overrides to start Celery worker)
- **Frontend** (`frontend/Dockerfile`)
- **PostgreSQL** (managed Render database)
- **Redis** (managed Render Redis)

Use object storage compatible with signed URL uploads (e.g., S3-compatible provider) if GCS is unavailable.

## 2) Environment configuration

### API + Worker

- `DATABASE_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `STORAGE_BACKEND` (`gcs` or local/provider-specific adaptation)
- Provider variables (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `TRANSCRIPTION_PROVIDER`)
- `OPENAI_API_KEY` when using OpenAI providers

### Frontend

- `NEXT_PUBLIC_API_BASE_URL=<render-api-url>`

## 3) Deployment steps

1. Connect repository to Render.
2. Create PostgreSQL and Redis managed resources.
3. Create API web service from backend Dockerfile.
4. Create Worker background service from same image with worker start command.
5. Create Frontend web service from frontend Dockerfile.
6. Inject environment variables and secrets in each service.
7. Deploy and verify health endpoints and UI flow.

## 4) Operational caveats on Render

- Heavy ffmpeg workloads may need high-CPU plans.
- Long-running media tasks should be isolated from API compute.
- Signed-upload strategy may need adjustments depending on storage provider integration.
- Ensure worker autoscaling (or manual scaling) aligns with upload throughput.

## 5) Verification checklist

- API `/health` and `/ready` return healthy.
- Upload init/complete flows enqueue jobs.
- Worker processes pipeline stages successfully.
- Review queue and semantic search pages display processed results.

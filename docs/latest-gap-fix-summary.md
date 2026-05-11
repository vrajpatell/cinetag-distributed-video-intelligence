# Latest production gap fix summary

This branch bundles incremental hardening across backend, Terraform, tests, and docs. Work is grouped so it can be split into smaller PRs (config/DB, search/embeddings, queue/Pub/Sub, auth, pagination, IAM, observability, docs).

## What was fixed

- **GCP database URL:** `DATABASE_URL` is optional; `APP_ENV=gcp` with `CLOUD_SQL_CONNECTION_NAME` + `DATABASE_PASSWORD` builds the Unix socket URL and avoids the Docker `postgres:5432` default. Explicit `DATABASE_URL` still overrides.
- **Secret / engine order:** `app/bootstrap.py` `ensure_preload()` runs before imports that create the DB engine; `get_engine()` is lazy; `get_settings.cache_clear()` refreshes settings after preload.
- **Semantic search:** `auto` skips pgvector when query embedding dimension ≠ `embedding_vector_dimension`; empty pgvector results fall back to Python JSON scan; forced `pgvector` fails loudly on mismatch; `python` mode always uses JSON scan. Python path applies the same video-level filters via joins.
- **Embeddings:** Worker logs JSON-only rows when mock/small dims; backfill script `python -m app.scripts.backfill_embedding_vectors` supports `--dry-run`, `--limit`, `--video-id`, `--reembed`.
- **Pub/Sub:** Versioned events (`schema_version`, `event_id`, `created_at`, `job_id`, `source`), message attributes, publisher retries, consumer validation, idempotent skip for completed/running jobs, DLQ IAM for the Pub/Sub service agent, subscription ack deadline / retry / retention / labels.
- **Auth:** Optional `AUTH_ENABLED` with `ADMIN_API_KEY`, `REVIEWER_API_KEY`, `SERVICE_API_KEY` (header `X-API-Key`). Uploads, job retry, tag mutations, manual tags, publish are protected when enabled.
- **Pagination:** `GET /api/videos`, `/api/jobs`, `/api/review` return `{ items, page, page_size, total, has_next }` with filters documented in code. Frontend uses paginated API with helpers to flatten for dashboards.
- **IAM / secrets:** Project-level `storage.objectAdmin` removed; bucket-level object admin for API/worker SAs; per-secret Secret Manager IAM; conditional Pub/Sub publisher/subscriber; Cloud Run env pulls DB and API keys from Secret Manager.
- **Observability:** `X-Request-ID` middleware and log format; Prometheus counters/histograms for API routes, auth failures, worker stage failures, search fallback, embedding backfill; optional OTLP endpoint when OTEL is enabled.
- **Terraform:** Optional Cloud CDN backend bucket (`enable_cloud_cdn`); `api_ingress` variable; migrate job VPC + DB secret env.

## Intentionally out of full scope

- Full HLS/ABR implementation (roadmap only).
- DRM.
- JWT/session auth (structure is API-key first; easy to extend).
- Replacing all project-level roles beyond those still required (e.g. Cloud SQL client has no bucket-level equivalent).

## Required GCP environment variables (reference)

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | `gcp` |
| `CLOUD_SQL_CONNECTION_NAME` | `project:region:instance` |
| `DATABASE_PASSWORD` | From Secret Manager or direct env |
| `SECRET_MANAGER_ENABLED` | `true` when using GCP Secret Manager |
| `AUTH_ENABLED` | `true` in production |
| `ADMIN_API_KEY` / `REVIEWER_API_KEY` / `SERVICE_API_KEY` | Mutation auth |
| `QUEUE_BACKEND` | `celery` or `pubsub` |
| `SEMANTIC_SEARCH_BACKEND` | `auto`, `pgvector`, or `python` |
| `OTEL_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT` | Optional tracing |

## Migration steps

1. Apply Terraform (new secrets may require importing existing `DATABASE_PASSWORD` if already created manually — see `docs/deploy-gcp-cloud-run.md`).
2. Run Alembic: `alembic upgrade head` (or Cloud Run job `cinetag-migrate`).
3. Optional: `python -m app.scripts.backfill_embedding_vectors --dry-run` then run without `--dry-run` after validating counts.

## Rollback

1. Revert deployment to previous container images.
2. If schema migration was applied, use Alembic downgrade only after confirming compatibility (pgvector index/columns).
3. Set `AUTH_ENABLED=false` only as a temporary measure if keys are misconfigured (not recommended long term).

## Manual validation commands

```bash
cd backend && python -m ruff check app && python -m pytest -q
cd frontend && npm ci && npm run typecheck && npm run build
terraform -chdir=infra/terraform fmt -recursive
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

## Test results (backend)

`100 passed` (ruff clean) on Python 3.13 in the development environment used for this change. Run the same commands in CI for your matrix.

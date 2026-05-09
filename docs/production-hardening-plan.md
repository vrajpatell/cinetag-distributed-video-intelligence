# Production Hardening Plan

## Why pgvector first

- It preserves the current Postgres-centric architecture and API contract.
- It removes Python full-scan semantic search bottlenecks with minimal system churn.
- It allows incremental backfill by storing both legacy JSON embeddings and vector columns.

## Why Pub/Sub decoupling now

- It enables managed, durable job dispatch for GCP production environments.
- It keeps Celery/Redis intact for local Docker Compose and existing worker behavior.
- It introduces a single publisher abstraction so routes do not depend on queue internals.

## Why Temporal/GKE are later phases

- Current worker stages are already functional and retryable with Celery.
- The highest near-term risk is data-plane scaling and network hardening, not orchestration replacement.
- Temporal/Argo/GKE migration adds operational complexity and is better tackled after queue + DB search stabilization.

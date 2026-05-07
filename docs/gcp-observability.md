# GCP Observability Guide

This document defines practical observability standards for CineTag on GCP across API, worker, and frontend services.

## 1) Observability goals

- Detect failures quickly in upload, processing, and publishing workflows.
- Diagnose bottlenecks per pipeline stage.
- Track user-facing reliability (search, review, jobs, upload).
- Create actionable alerts with low noise.

## 2) Telemetry sources

- **Cloud Logging**: structured application logs from Cloud Run services.
- **Cloud Monitoring**: service-level metrics, dashboards, and alert policies.
- **Application metrics**: internal pipeline/job counters exposed by backend observability modules.

## 3) Golden signals by service

### API (`cinetag-api`)
- Request rate
- Error rate (4xx/5xx split)
- p50/p95/p99 latency
- Upload-init and upload-complete error counts
- Search endpoint latency and success ratio

### Worker (`cinetag-worker`)
- Jobs started/completed/failed
- Stage-level retry count
- Stage duration distribution
- Queue lag / time-to-start
- Partial-completion count (provider fallback)

### Frontend (`cinetag-frontend`)
- Request latency
- Non-2xx response rate
- Build/version fingerprint in logs for incident correlation

## 4) Suggested dashboards

1. **Executive reliability dashboard**
   - API uptime, worker failure rate, publish success rate.
2. **Pipeline operations dashboard**
   - Job throughput, stage durations, retries by stage.
3. **Search quality/perf dashboard**
   - Semantic query latency, result counts, provider error fallback events.
4. **Cost/utilization dashboard**
   - Cloud Run instance count, vCPU/memory trends, Redis/SQL utilization.

## 5) Alert policy baseline

Recommended initial alerts:

- API 5xx error ratio > 2% for 10m.
- API p95 latency > 2s for 15m.
- Worker job failure ratio > 5% for 15m.
- Queue lag above threshold (environment-specific) for 10m.
- No completed jobs in expected active windows.
- Cloud SQL CPU > 80% sustained 15m.
- Redis memory > 80% sustained 15m.

## 6) Log design recommendations

Include these fields in structured logs where possible:

- `service` (`api`, `worker`, `frontend`)
- `video_id`, `job_id`
- `stage_name`, `attempt`, `duration_ms`
- `provider` and `provider_fallback` flags
- `request_id` / trace context

This enables fast filtered debugging in Cloud Logging and direct linking from alerts.

## 7) Incident response playbook (lightweight)

1. Detect alert and identify affected plane (ingestion, processing, discovery).
2. Validate health endpoints and deployment changes in last hour.
3. Check queue lag and worker logs for hot stage failures.
4. Determine scope (single stage, provider outage, infra saturation).
5. Mitigate (scale worker, rollback, switch provider mode, pause intake if needed).
6. Document timeline and corrective actions.

## 8) Maturity roadmap

- **Phase 1**: baseline logs + alerts.
- **Phase 2**: SLOs for upload-to-review-ready latency and API availability.
- **Phase 3**: tracing across upload/init/worker stage chain with end-to-end correlation IDs.
- **Phase 4**: anomaly detection for search relevance and tag-quality drift.

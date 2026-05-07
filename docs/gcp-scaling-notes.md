# GCP Scaling Notes

This document summarizes scaling strategy for CineTag services on GCP.

## 1) Scaling principles

- Scale API, worker, and frontend independently.
- Treat ingestion and processing as decoupled planes.
- Optimize for queue stability and predictable stage latency.
- Keep stateful bottlenecks (SQL/Redis) ahead of stateless scale-outs.

## 2) Service-specific scaling

### API service

Scale primarily on concurrent request load.

- Increase max instances for traffic spikes.
- Set minimum instances for cold-start-sensitive workloads.
- Watch p95 latency and 5xx rates.

### Worker service

Scale on backlog and processing latency.

- Increase worker replicas and/or concurrency for queue drain.
- Separate heavy vs light workloads if stage durations diverge significantly.
- Use retry/backoff settings to avoid hot-loop failures.

### Frontend service

Scale for read-heavy burst traffic.

- Keep enough minimum instances for consistent TTFB.
- Monitor cache and CDN strategy if adding static edge caching.

## 3) Stateful bottleneck planning

### Cloud SQL

- Right-size CPU/memory as job throughput grows.
- Add read replicas if read-heavy query load develops.
- Tune indexes for search/filter routes.

### Memorystore Redis

- Monitor memory headroom and connection counts.
- Ensure queue payload sizing stays bounded.
- Plan tier upgrades before sustained saturation.

### Cloud Storage

- No practical scaling concern for object count in this use case.
- Focus on request/egress cost, lifecycle policy, and multipart upload behavior.

## 4) Queue-depth and SLO guidance

Track and alert on:

- Queue age / time-to-start processing
- End-to-end upload-to-review-ready latency
- Stage-specific p95 durations
- Retry rates per stage

If queue age grows while worker CPU is low, inspect external provider latency (LLM/STT/embeddings) or downstream contention.

## 5) Horizontal partitioning path

When throughput increases significantly:

1. Split queues by workload class (e.g., short-form vs long-form).
2. Run dedicated worker pools with tailored CPU/memory.
3. Isolate failure domains by pipeline stage family.
4. Move semantic search to a managed vector index for sub-second ANN.

## 6) Cost-performance levers

- Tune Cloud Run min instances to balance cold starts vs idle spend.
- Adjust worker CPU allocation per stage complexity.
- Cap unnecessary retries for deterministic hard failures.
- Use storage lifecycle and retention policies to control object growth.

## 7) Load testing recommendations

- Run synthetic uploads across realistic size distributions.
- Simulate provider latency and intermittent failures.
- Validate autoscaling response and steady-state queue drain.
- Record breakpoints and define scaling runbooks from empirical limits.

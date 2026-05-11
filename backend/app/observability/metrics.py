from prometheus_client import Counter, Histogram

jobs_total = Counter("cinetag_jobs_total", "Total jobs")
jobs_failed_total = Counter("cinetag_jobs_failed_total", "Failed jobs")
stage_duration = Histogram("cinetag_stage_duration_seconds", "Stage duration", ["stage"])
videos_processed = Counter("cinetag_videos_processed_total", "Processed videos")
tags_generated = Counter("cinetag_tags_generated_total", "Generated tags")
tags_approved = Counter("cinetag_tags_approved_total", "Approved tags")
tags_rejected = Counter("cinetag_tags_rejected_total", "Rejected tags")
queue_publish_total = Counter(
    "cinetag_queue_publish_total",
    "Queue publish outcomes",
    ["backend", "status"],
)
semantic_search_total = Counter(
    "cinetag_semantic_search_total",
    "Semantic search calls",
    ["backend", "status"],
)
semantic_search_latency_seconds = Histogram(
    "cinetag_semantic_search_latency_seconds",
    "Semantic search latency",
    ["backend"],
)
semantic_search_fallback_total = Counter(
    "cinetag_semantic_search_fallback_total",
    "Semantic search pgvector-to-python fallbacks",
)
pubsub_messages_total = Counter(
    "cinetag_pubsub_messages_total",
    "Pub/Sub message outcomes",
    ["status"],
)
api_request_total = Counter(
    "cinetag_api_request_total",
    "API HTTP requests",
    ["route", "status_code"],
)
api_request_duration_seconds = Histogram(
    "cinetag_api_request_duration_seconds",
    "API request duration",
    ["route"],
)
worker_stage_failures_total = Counter(
    "cinetag_worker_stage_failures_total",
    "Worker pipeline stage failures",
    ["stage"],
)
embedding_backfill_total = Counter(
    "cinetag_embedding_backfill_total",
    "Embedding vector backfill operations",
    ["mode"],
)
auth_failures_total = Counter(
    "cinetag_auth_failures_total",
    "API authentication failures",
)

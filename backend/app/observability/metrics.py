from prometheus_client import Counter, Histogram
jobs_total = Counter("cinetag_jobs_total", "Total jobs")
jobs_failed_total = Counter("cinetag_jobs_failed_total", "Failed jobs")
stage_duration = Histogram("cinetag_stage_duration_seconds", "Stage duration", ["stage"])
videos_processed = Counter("cinetag_videos_processed_total", "Processed videos")
tags_generated = Counter("cinetag_tags_generated_total", "Generated tags")
tags_approved = Counter("cinetag_tags_approved_total", "Approved tags")
tags_rejected = Counter("cinetag_tags_rejected_total", "Rejected tags")

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"
EVENT_TYPE_PROCESSING_JOB_CREATED = "processing_job.created"


def build_processing_job_event(
    job_id: int,
    *,
    source: str = "cinetag-api",
    attempt: int | None = None,
) -> dict[str, Any]:
    ev: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event_type": EVENT_TYPE_PROCESSING_JOB_CREATED,
        "event_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "source": source,
    }
    if attempt is not None:
        ev["attempt"] = attempt
    return ev


def parse_processing_job_event(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Validate Pub/Sub JSON body; return (job_id, payload) or raise ValueError."""
    ver = payload.get("schema_version")
    if ver != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {ver!r}")
    et = payload.get("event_type")
    if et != EVENT_TYPE_PROCESSING_JOB_CREATED:
        raise ValueError(f"unexpected event_type: {et!r}")
    if "job_id" not in payload:
        raise ValueError("missing job_id")
    try:
        job_id = int(payload["job_id"])
    except (TypeError, ValueError) as exc:
        raise ValueError("job_id must be an integer") from exc
    return job_id, payload

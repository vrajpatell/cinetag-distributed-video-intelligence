from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/health')
def health():
    """Liveness probe.

    Intentionally dependency-free: returns OK if the API process is up.
    Cloud Run liveness probes should point here.
    """
    return {'status': 'ok', 'env': settings.app_env}


@router.get('/ready')
def ready(response: Response, db: Session = Depends(get_db)):
    """Readiness probe.

    Verifies the API can serve real traffic by issuing a fast ``SELECT 1``
    against the configured database. On failure we return HTTP 503 with a
    structured payload so Cloud Run / load balancers can flip the replica
    out of rotation, and the frontend "All systems" pill turns red.
    """
    db_ok = False
    db_error: str | None = None
    try:
        db.execute(text('SELECT 1'))
        db_ok = True
    except Exception as exc:
        db_error = type(exc).__name__
        logger.warning('readiness_db_check_failed error=%s', db_error)

    payload = {
        'status': 'ready' if db_ok else 'degraded',
        'env': settings.app_env,
        'checks': {'database': 'ok' if db_ok else 'down'},
    }
    if not db_ok:
        # Include a high-level error class so operators can debug without
        # exposing connection strings or stack traces.
        payload['checks']['database_error'] = db_error or 'unknown'
        response.status_code = 503
    return payload

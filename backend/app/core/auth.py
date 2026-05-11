"""API key authentication (optional). When AUTH_ENABLED=false, mutations stay open for local dev."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.core.config import settings
from app.observability.metrics import auth_failures_total

_LOG = logging.getLogger(__name__)


class Role(str, Enum):
    admin = "admin"
    reviewer = "reviewer"
    viewer = "viewer"
    service = "service"


def _roles_for_api_key(api_key: str | None) -> set[Role]:
    if not api_key:
        return set()
    roles: set[Role] = set()
    if settings.admin_api_key and api_key == settings.admin_api_key:
        roles.update({Role.admin, Role.reviewer, Role.viewer})
    if settings.reviewer_api_key and api_key == settings.reviewer_api_key:
        roles.update({Role.reviewer, Role.viewer})
    if settings.service_api_key and api_key == settings.service_api_key:
        roles.add(Role.service)
    return roles


def require_roles(*allowed: Role):
    allowed_set = set(allowed)

    def _dep(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        if not settings.auth_enabled:
            return None
        if not settings.admin_api_key and not settings.reviewer_api_key and not settings.service_api_key:
            _LOG.warning("auth_enabled_without_keys_configured")
        roles = _roles_for_api_key(x_api_key)
        if roles & allowed_set:
            return None
        auth_failures_total.inc()
        _LOG.warning("auth_denied allowed=%s", [r.value for r in allowed])
        raise HTTPException(status_code=401, detail="Unauthorized")

    return _dep


RequireAdminOrService = Annotated[None, Depends(require_roles(Role.admin, Role.service))]
RequireReviewerOrAdmin = Annotated[None, Depends(require_roles(Role.admin, Role.reviewer))]
RequireViewerOrAbove = Annotated[
    None,
    Depends(require_roles(Role.admin, Role.reviewer, Role.viewer, Role.service)),
]

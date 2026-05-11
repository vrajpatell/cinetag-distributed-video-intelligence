from __future__ import annotations

import os
from typing import Iterable

from app.core.config import settings


def _load_from_secret_manager(secret_name: str, version: str = "latest") -> str | None:
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    project = settings.gcp_project_id
    name = f"projects/{project}/secrets/{secret_name}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


def get_secret(name: str, env_fallback: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    if env_fallback and os.getenv(env_fallback):
        return os.getenv(env_fallback)
    if settings.secret_manager_enabled and settings.app_env == "gcp":
        return _load_from_secret_manager(name)
    return None


def preload_known_secrets(
    secret_names: Iterable[str] = (
        "DATABASE_PASSWORD",
        "OPENAI_API_KEY",
        "APP_SECRET_KEY",
        "JWT_SECRET",
        "ADMIN_API_KEY",
        "REVIEWER_API_KEY",
        "SERVICE_API_KEY",
    ),
) -> None:
    for name in secret_names:
        value = get_secret(name)
        if value and not os.getenv(name):
            os.environ[name] = value

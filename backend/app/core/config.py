from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOG = logging.getLogger(__name__)

# Default Docker Compose Postgres service hostname (never used when APP_ENV=gcp unless DATABASE_URL is set).
LOCAL_DATABASE_DEFAULT = "postgresql+psycopg://cinetag:cinetag@postgres:5432/cinetag"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CineTag Pipeline"
    app_env: Literal["local", "gcp"] = "local"

    gcp_project_id: str = "cinetag-distributed-video"
    gcp_region: str = "us-central1"

    storage_backend: Literal["minio", "gcs"] = "minio"
    gcs_bucket_name: str | None = None
    local_storage_dir: str = "/tmp/cinetag-store"

    database_backend: str = "postgres"
    database_url: str | None = Field(
        default=None,
        description="Explicit SQLAlchemy URL. When unset, local uses LOCAL_DATABASE_DEFAULT; GCP uses Cloud SQL socket URL.",
    )
    cloud_sql_connection_name: str | None = Field(
        default=None,
        description="project:region:instance for Cloud SQL Unix socket (APP_ENV=gcp).",
    )
    gcp_database_name: str = Field(default="cinetag", validation_alias="GCP_DATABASE_NAME")
    gcp_database_user: str = Field(default="cinetag_app", validation_alias="GCP_DATABASE_USER")
    database_password: str | None = Field(default=None, validation_alias="DATABASE_PASSWORD")

    queue_backend: Literal["celery", "pubsub", "redis"] = "celery"
    redis_url: str = "redis://redis:6379/0"
    broker_url: str | None = None
    result_backend: str | None = None
    worker_pool: str = "solo"
    worker_concurrency: int = 1
    pubsub_topic_name: str = "cinetag-processing-jobs"
    pubsub_subscription_name: str = "cinetag-processing-jobs-sub"
    pubsub_dead_letter_topic_name: str = "cinetag-processing-jobs-dlq"

    semantic_search_backend: Literal["auto", "pgvector", "python"] = "auto"
    pgvector_enabled: bool = True
    embedding_vector_dimension: int = 1536

    llm_provider: str = "mock"
    embedding_provider: str = "mock"
    transcription_provider: str = "mock"
    openai_api_key: str | None = None
    openai_llm_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_transcription_model: str = "whisper-1"
    scene_detection_threshold: float = 0.35

    provider_strict: bool = False
    media_strict: bool = False

    secret_manager_enabled: bool = False
    log_level: str = "INFO"
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_service_name: str = Field(default="cinetag-api", validation_alias="OTEL_SERVICE_NAME")

    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    max_upload_size_mb: int = 512

    auth_enabled: bool = Field(default=False, validation_alias="AUTH_ENABLED")
    admin_api_key: str | None = Field(default=None, validation_alias="ADMIN_API_KEY")
    reviewer_api_key: str | None = Field(default=None, validation_alias="REVIEWER_API_KEY")
    service_api_key: str | None = Field(default=None, validation_alias="SERVICE_API_KEY")

    @model_validator(mode="after")
    def _warn_gcp_docker_db_host(self) -> Settings:
        u = self.database_url
        if self.app_env == "gcp" and u and "@postgres:" in u:
            _LOG.warning(
                "database_config_uses_postgres_service_host_in_gcp",
                extra={
                    "hint": "Prefer CLOUD_SQL_CONNECTION_NAME + DATABASE_PASSWORD or a real DATABASE_URL."
                },
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def effective_database_url(self) -> str:
        if self.database_url and str(self.database_url).strip():
            return str(self.database_url).strip()

        if self.app_env == "gcp":
            if not self.cloud_sql_connection_name:
                msg = "APP_ENV=gcp requires DATABASE_URL or CLOUD_SQL_CONNECTION_NAME"
                _LOG.error("database_config_error", extra={"reason": msg})
                raise ValueError(msg)
            if not self.database_password:
                msg = (
                    "GCP database password missing: set DATABASE_PASSWORD in the environment "
                    "(for example via Secret Manager preload or Cloud Run secret env) "
                    "before creating the SQLAlchemy engine"
                )
                _LOG.error("database_config_error", extra={"reason": msg})
                raise ValueError(msg)
            return (
                f"postgresql+psycopg://{self.gcp_database_user}:{self.database_password}@/"
                f"{self.gcp_database_name}?host=/cloudsql/{self.cloud_sql_connection_name}"
            )

        return LOCAL_DATABASE_DEFAULT

    @staticmethod
    def _with_redis_db_index(url: str, db_index: int) -> str:
        prefix, sep, suffix = url.partition("?")
        if "/" not in prefix.split("://", 1)[-1]:
            updated = f"{prefix}/{db_index}"
        else:
            base, _, _db = prefix.rpartition("/")
            updated = f"{base}/{db_index}"
        return f"{updated}{sep}{suffix}" if sep else updated

    @property
    def effective_broker_url(self) -> str:
        if self.broker_url:
            return self.broker_url
        return self._with_redis_db_index(self.redis_url, 1)

    @property
    def effective_result_backend(self) -> str:
        if self.result_backend:
            return self.result_backend
        return self._with_redis_db_index(self.redis_url, 2)


def build_cloudsql_database_url(
    project_id: str, region: str, instance: str, database: str, user: str, password: str
) -> str:
    conn_name = f"{project_id}:{region}:{instance}"
    return (
        f"postgresql+psycopg://{user}:{password}@/{database}?host=/cloudsql/{conn_name}"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


class _SettingsProxy:
    """Lazy settings access; supports ``patch.object(settings, ...)`` in tests.

    Patches store values in an override dict so teardown can ``delattr`` without
    mutating the underlying cached ``Settings`` instance.
    """

    __slots__ = ("_overrides",)

    def __init__(self) -> None:
        object.__setattr__(self, "_overrides", {})

    def __getattr__(self, name: str):
        o = object.__getattribute__(self, "_overrides")
        if name in o:
            return o[name]
        return getattr(get_settings(), name)

    def __setattr__(self, name: str, value) -> None:
        if name == "_overrides":
            object.__setattr__(self, name, value)
        else:
            object.__getattribute__(self, "_overrides")[name] = value

    def __delattr__(self, name: str) -> None:
        o = object.__getattribute__(self, "_overrides")
        if name in o:
            del o[name]
            return
        raise AttributeError(name)


settings = _SettingsProxy()

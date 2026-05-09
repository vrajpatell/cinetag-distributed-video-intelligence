from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    app_name: str = 'CineTag Pipeline'
    app_env: Literal['local', 'gcp'] = 'local'

    gcp_project_id: str = 'cinetag-distributed-video'
    gcp_region: str = 'us-central1'

    storage_backend: Literal['minio', 'gcs'] = 'minio'
    gcs_bucket_name: str | None = None
    local_storage_dir: str = '/tmp/cinetag-store'

    database_backend: str = 'postgres'
    database_url: str = 'postgresql+psycopg://cinetag:cinetag@postgres:5432/cinetag'
    cloud_sql_connection_name: str | None = None
    gcp_database_name: str = 'cinetag'
    gcp_database_user: str = 'cinetag_app'
    database_password: str | None = None

    queue_backend: Literal['celery', 'pubsub', 'redis'] = 'celery'
    redis_url: str = 'redis://redis:6379/0'
    broker_url: str | None = None
    result_backend: str | None = None
    worker_pool: str = 'solo'
    worker_concurrency: int = 1
    pubsub_topic_name: str = 'cinetag-processing-jobs'
    pubsub_subscription_name: str = 'cinetag-processing-jobs-sub'
    pubsub_dead_letter_topic_name: str = 'cinetag-processing-jobs-dlq'

    semantic_search_backend: Literal['auto', 'pgvector', 'python'] = 'auto'
    pgvector_enabled: bool = True
    embedding_vector_dimension: int = 1536

    llm_provider: str = 'mock'
    embedding_provider: str = 'mock'
    transcription_provider: str = 'mock'
    openai_api_key: str | None = None
    openai_llm_model: str = 'gpt-4o-mini'
    openai_embedding_model: str = 'text-embedding-3-small'
    openai_transcription_model: str = 'whisper-1'
    scene_detection_threshold: float = 0.35

    # When true, configured providers must succeed. Failures raise instead of
    # silently falling back to the mock implementations -- the worker then
    # marks the job failed/partially_completed for operator review.
    provider_strict: bool = False
    # When true, surface ffmpeg/ffprobe/audio-extraction errors as failures
    # instead of using deterministic placeholders so dev demos still complete.
    media_strict: bool = False

    secret_manager_enabled: bool = False
    log_level: str = 'INFO'
    otel_enabled: bool = False

    cors_allowed_origins: str = 'http://localhost:5173,http://localhost:3000'
    max_upload_size_mb: int = 512

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(',') if o.strip()]

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.cloud_sql_connection_name and self.database_password:
            return (
                f"postgresql+psycopg://{self.gcp_database_user}:{self.database_password}@/"
                f"{self.gcp_database_name}?host=/cloudsql/{self.cloud_sql_connection_name}"
            )
        raise ValueError('DATABASE_URL or Cloud SQL settings must be provided')

    @staticmethod
    def _with_redis_db_index(url: str, db_index: int) -> str:
        # Preserve query/fragment while replacing only the path's DB index.
        # Handles redis://host:port and redis://host:port/<db>.
        prefix, sep, suffix = url.partition('?')
        if '/' not in prefix.split('://', 1)[-1]:
            updated = f'{prefix}/{db_index}'
        else:
            base, _, _db = prefix.rpartition('/')
            updated = f'{base}/{db_index}'
        return f'{updated}{sep}{suffix}' if sep else updated

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


def build_cloudsql_database_url(project_id: str, region: str, instance: str, database: str, user: str, password: str) -> str:
    conn_name = f'{project_id}:{region}:{instance}'
    return f'postgresql+psycopg://{user}:{password}@/{database}?host=/cloudsql/{conn_name}'


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

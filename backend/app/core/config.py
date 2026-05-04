from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "CineTag Pipeline"
    database_url: str = "postgresql+psycopg://cinetag:cinetag@postgres:5432/cinetag"
    redis_url: str = "redis://redis:6379/0"
    broker_url: str = "redis://redis:6379/1"
    result_backend: str = "redis://redis:6379/2"
    object_store_mode: str = "local"
    local_storage_dir: str = "/tmp/cinetag-store"
    llm_provider: str = "mock"
    openai_api_key: str | None = None

settings = Settings()

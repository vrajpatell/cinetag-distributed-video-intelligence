from app.core.config import Settings


def test_effective_queue_urls_default_from_redis_url():
    settings = Settings(redis_url="redis://10.0.0.5:6379/0", broker_url=None, result_backend=None)
    assert settings.effective_broker_url == "redis://10.0.0.5:6379/1"
    assert settings.effective_result_backend == "redis://10.0.0.5:6379/2"


def test_effective_queue_urls_respect_explicit_overrides():
    settings = Settings(
        redis_url="redis://10.0.0.5:6379/0",
        broker_url="redis://10.0.0.5:6379/9",
        result_backend="redis://10.0.0.5:6379/8",
    )
    assert settings.effective_broker_url == "redis://10.0.0.5:6379/9"
    assert settings.effective_result_backend == "redis://10.0.0.5:6379/8"

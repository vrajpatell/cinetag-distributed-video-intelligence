from app.core import secrets


def test_secret_env_fallback(monkeypatch):
    monkeypatch.setenv('DATABASE_PASSWORD', 'x')
    assert secrets.get_secret('DATABASE_PASSWORD') == 'x'


def test_secret_manager_disabled(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('SECRET_MANAGER_ENABLED', 'false')
    assert secrets.get_secret('OPENAI_API_KEY') is None

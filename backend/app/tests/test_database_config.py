"""Database URL resolution for local vs GCP."""

from __future__ import annotations

import pytest

from app.core.config import get_settings


def test_local_uses_database_url_when_set(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    get_settings.cache_clear()
    s = get_settings()
    assert "localhost" in s.effective_database_url


def test_local_falls_back_to_compose_default_without_database_url(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    s = get_settings()
    assert s.database_url is None
    assert "@postgres:5432" in s.effective_database_url


def test_gcp_builds_cloud_sql_url_without_database_url(monkeypatch):
    monkeypatch.setenv("APP_ENV", "gcp")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CLOUD_SQL_CONNECTION_NAME", "proj:reg:inst")
    monkeypatch.setenv("DATABASE_PASSWORD", "secret")
    get_settings.cache_clear()
    s = get_settings()
    url = s.effective_database_url
    assert "/cloudsql/proj:reg:inst" in url
    assert "postgres:5432" not in url


def test_gcp_explicit_database_url_override(monkeypatch):
    monkeypatch.setenv("APP_ENV", "gcp")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://u:pw@10.0.0.3:5432/cinetag",
    )
    monkeypatch.setenv("CLOUD_SQL_CONNECTION_NAME", "proj:reg:inst")
    get_settings.cache_clear()
    s = get_settings()
    assert s.effective_database_url.startswith("postgresql+psycopg://u:pw@10.0.0.3")


def test_gcp_missing_password_raises_clearly(monkeypatch):
    monkeypatch.setenv("APP_ENV", "gcp")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CLOUD_SQL_CONNECTION_NAME", "proj:reg:inst")
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    get_settings.cache_clear()
    s = get_settings()
    with pytest.raises(ValueError, match="password"):
        _ = s.effective_database_url


def test_gcp_missing_cloud_sql_and_database_url_raises(monkeypatch):
    monkeypatch.setenv("APP_ENV", "gcp")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUD_SQL_CONNECTION_NAME", raising=False)
    monkeypatch.setenv("DATABASE_PASSWORD", "x")
    get_settings.cache_clear()
    s = get_settings()
    with pytest.raises(ValueError, match="CLOUD_SQL_CONNECTION_NAME"):
        _ = s.effective_database_url


def test_gcp_password_from_env_used_in_socket_url(monkeypatch):
    monkeypatch.setenv("APP_ENV", "gcp")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CLOUD_SQL_CONNECTION_NAME", "p:r:i")
    monkeypatch.setenv("DATABASE_PASSWORD", "secretpw")
    get_settings.cache_clear()
    s = get_settings()
    url = s.effective_database_url
    assert "/cloudsql/p:r:i" in url
    assert "secretpw" in url

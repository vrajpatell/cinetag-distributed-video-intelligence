"""Liveness and readiness probe behavior."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_is_dependency_free():
    """Liveness must answer 200 even with no DB session override."""
    c = TestClient(app)
    res = c.get('/health')
    assert res.status_code == 200
    body = res.json()
    assert body['status'] == 'ok'
    assert 'env' in body


def test_ready_returns_200_when_db_reachable(client):
    """/ready uses the conftest-overridden in-memory SQLite — should be OK."""
    res = client.get('/ready')
    assert res.status_code == 200
    body = res.json()
    assert body['status'] == 'ready'
    assert body['checks']['database'] == 'ok'


def test_ready_returns_503_when_db_unreachable(client):
    """A failing SELECT 1 should flip readiness to degraded with HTTP 503."""

    def _broken_execute(self, *args, **kwargs):
        raise RuntimeError("database connection lost")

    with patch('sqlalchemy.orm.Session.execute', _broken_execute):
        res = client.get('/ready')

    assert res.status_code == 503
    body = res.json()
    assert body['status'] == 'degraded'
    assert body['checks']['database'] == 'down'
    assert 'database_error' in body['checks']
    # Detail must NOT leak the raw exception message.
    assert 'connection lost' not in res.text

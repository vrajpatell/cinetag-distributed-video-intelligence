from fastapi.testclient import TestClient

from app.core.config import Settings
from app.workers import worker_service_main


class _HealthyProc:
    def poll(self):
        return None


def test_worker_service_module_imports():
    assert worker_service_main.app is not None


def test_worker_service_health_ok():
    c = TestClient(worker_service_main.app)
    r = c.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_worker_service_ready_ok_when_worker_healthy():
    worker_service_main.runtime._process = _HealthyProc()
    worker_service_main.runtime._healthy = True

    c = TestClient(worker_service_main.app)
    r = c.get('/ready')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_worker_command_celery(monkeypatch):
    monkeypatch.setattr(
        worker_service_main,
        'settings',
        Settings(queue_backend='celery'),
    )
    assert worker_service_main._worker_command() == ['python', '-m', 'app.workers.worker_main']


def test_worker_command_pubsub(monkeypatch):
    monkeypatch.setattr(
        worker_service_main,
        'settings',
        Settings(queue_backend='pubsub'),
    )
    assert worker_service_main._worker_command() == ['python', '-m', 'app.workers.pubsub_consumer']


def test_worker_command_redis_uses_celery_worker(monkeypatch):
    monkeypatch.setattr(
        worker_service_main,
        'settings',
        Settings(queue_backend='redis'),
    )
    assert worker_service_main._worker_command() == ['python', '-m', 'app.workers.worker_main']

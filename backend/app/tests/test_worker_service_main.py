from fastapi.testclient import TestClient

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

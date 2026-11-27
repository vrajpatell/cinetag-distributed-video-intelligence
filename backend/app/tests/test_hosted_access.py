import pytest

from app.core.config import get_settings


@pytest.fixture
def protected(monkeypatch):
    config = get_settings()
    monkeypatch.setattr(config, "auth_enabled", True)
    monkeypatch.setattr(config, "admin_api_key", "admin-test")
    monkeypatch.setattr(config, "reviewer_api_key", "reviewer-test")
    monkeypatch.setattr(config, "service_api_key", "service-test")
    return config


@pytest.mark.parametrize(
    "path",
    [
        "/api/videos",
        "/api/videos/1/transcript",
        "/api/videos/1/playback",
        "/api/jobs",
        "/api/review",
        "/api/catalog/schema",
        "/api/videos/1/notes",
        "/metrics",
        "/openapi.json",
    ],
)
def test_anonymous_requests_stop_before_private_handlers(client, protected, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("name,value", [("K_SERVICE", "cinetag-api"), ("RENDER", "true")])
def test_managed_service_cannot_disable_auth(client, protected, monkeypatch, name, value):
    monkeypatch.setattr(protected, "auth_enabled", False)
    monkeypatch.setenv(name, value)
    assert client.get("/api/catalog/schema").status_code == 401


def test_gcp_without_keys_fails_closed(client, protected, monkeypatch):
    monkeypatch.setattr(protected, "auth_enabled", False)
    monkeypatch.setattr(protected, "app_env", "gcp")
    for name in ("admin_api_key", "service_api_key", "reviewer_api_key"):
        monkeypatch.setattr(protected, name, None)
    assert client.get("/api/videos", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_role_checks_still_apply_with_authenticated_request(client, protected):
    headers = {"X-API-Key": "reviewer-test"}
    assert client.get("/api/catalog/schema", headers=headers).status_code == 200
    response = client.put("/api/uploads/direct/originals/test.mp4", headers=headers, content=b"x")
    assert response.status_code == 401


def test_preflight_permits_auth_header_without_releasing_data(client, protected):
    response = client.options(
        "/api/videos",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-api-key",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert client.get("/api/videos", headers={"Origin": "http://localhost:3000"}).status_code == 401

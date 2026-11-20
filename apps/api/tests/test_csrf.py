from fastapi.testclient import TestClient

from tutor_api.core.settings import Settings
from tutor_api.main import create_app


def _client() -> TestClient:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://tutor:tutor@127.0.0.1:5432/tutor",
        cors_origins=["http://localhost:3000"],
    )
    return TestClient(create_app(settings))


def test_cookie_login_from_another_origin_is_rejected() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "school_code": "demo",
                "username": "ada",
                "password": "classroom-key",
            },
            headers={"origin": "http://evil.example"},
        )
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_rejected"


def test_allowed_origin_without_the_requested_with_header_is_rejected() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "school_code": "demo",
                "username": "ada",
                "password": "classroom-key",
            },
            headers={"origin": "http://localhost:3000"},
        )
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_rejected"

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tutor_api.core.errors import DomainError
from tutor_api.core.settings import Settings
from tutor_api.main import create_app


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql+asyncpg://tutor:tutor@127.0.0.1:5432/tutor",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_unknown_path_is_problem_json(client: TestClient) -> None:
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "not_found"
    assert body["status"] == 404
    assert body["instance"] == "/missing"


def test_domain_error_is_problem_json() -> None:
    app = create_app(_settings())

    @app.get("/_test/blocked")
    async def blocked() -> dict[str, str]:
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="You cannot do that.",
        )

    with TestClient(app) as client:
        response = client.get("/_test/blocked")
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert response.json()["detail"] == "You cannot do that."


def test_validation_error_is_problem_json() -> None:
    app = create_app(_settings())

    @app.get("/_test/items/{item_id}")
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    with TestClient(app) as client:
        response = client.get("/_test/items/not-a-number")
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"


def test_unexpected_error_hides_the_message() -> None:
    app = create_app(_settings())

    @app.get("/_test/boom")
    async def boom() -> dict[str, str]:
        raise RuntimeError("disk serial 1234")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/boom")
    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert "1234" not in response.text


def test_docs_are_disabled_in_production(monkeypatch: object) -> None:
    del monkeypatch
    app = create_app(_settings(app_env="production", docs_enabled=False))
    with TestClient(app) as client:
        assert client.get("/api/docs").status_code == 404
        assert client.get("/api/openapi.json").status_code == 404


def test_hsts_in_production() -> None:
    app = create_app(_settings(app_env="production", docs_enabled=False))
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert "max-age=31536000" in response.headers["strict-transport-security"]

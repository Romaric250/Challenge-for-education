from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_request_id_is_returned(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "req-12345678"})
    assert response.headers["x-request-id"] == "req-12345678"


def test_unsafe_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "bad id"})
    assert response.headers["x-request-id"] != "bad id"
    assert response.headers["x-request-id"]


def test_security_headers(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "strict-transport-security" not in response.headers


def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/health/live",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_blocks_unknown_origin(client: TestClient) -> None:
    response = client.get("/health/live", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_service_identity(client: TestClient) -> None:
    response = client.get("/api/v1/service")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Rwanda AI Tutor"
    assert body["api_version"] == "v1"
    assert body["version"]


def test_openapi_document_lists_health(client: TestClient) -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/api/v1/service" in paths

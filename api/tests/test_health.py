from fastapi.testclient import TestClient


def test_root_redirects_to_useful_info(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "version" in body
    assert "environment" in body


def test_detailed_health_check(client: TestClient) -> None:
    response = client.get("/health/detailed")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["services"]["database"] == "healthy"
    assert body["services"]["redis"] == "healthy"

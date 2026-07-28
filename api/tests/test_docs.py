"""Confirms the interactive API docs (Swagger UI / ReDoc / OpenAPI) are mounted."""

from fastapi.testclient import TestClient


def test_swagger_ui_is_mounted_at_docs(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_redoc_is_mounted(client: TestClient) -> None:
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_schema_lists_health_endpoints(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/health" in schema["paths"]
    assert "/health/detailed" in schema["paths"]
    assert "get" in schema["paths"]["/health"]

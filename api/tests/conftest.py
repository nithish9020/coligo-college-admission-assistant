import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI test client bound to the app instance."""
    return TestClient(app)

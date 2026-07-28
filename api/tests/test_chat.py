from typing import AsyncIterator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.main import app
from api.models import DocumentChunk


@pytest.fixture
def mock_db_session() -> Generator[AsyncMock, None, None]:
    """Mock the FastAPI get_db dependency for the chat test suite."""
    mock_session = AsyncMock(spec=AsyncSession)

    # By default, mock database execution returns one matching chunk
    mock_result = MagicMock()
    mock_chunk = DocumentChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        text_content="Fees for Computer Science at Sri Krishna College is 70,000 INR per semester.",
        sha256="dummy_sha256",
    )
    mock_result.all.return_value = [(mock_chunk, "/docs/SriKrishna.pdf")]
    mock_session.execute.return_value = mock_result

    async def override_get_db() -> AsyncIterator[AsyncMock]:
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    yield mock_session
    app.dependency_overrides.clear()


@pytest.fixture
def mock_embeddings() -> Generator[MagicMock, None, None]:
    """Mock get_embeddings helper to avoid active Gemini API HTTP requests."""
    with patch("api.services.rag_service.get_embeddings") as mock:
        mock.return_value = [[0.05] * 768]
        yield mock


@pytest.fixture
def mock_llm() -> Generator[MagicMock, None, None]:
    """Mock LLM response helper to avoid active Gemini LLM generation calls."""
    with patch("api.services.rag_service.generate_response_from_llm") as mock:
        mock.return_value = (
            "According to the context, the computer science fee at "
            "Sri Krishna College is 70,000 INR per semester."
        )
        yield mock


def test_chat_success(
    client: TestClient,
    mock_db_session: AsyncMock,
    mock_embeddings: MagicMock,
    mock_llm: MagicMock,
) -> None:
    """Verify that a valid message successfully retrieves chunks and returns LLM answer."""
    payload = {"message": "What is the fee for CS?"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "sources" in data
    assert "Sri Krishna College is 70,000 INR" in data["response"]
    assert data["sources"] == ["/docs/SriKrishna.pdf"]

    # Verify our service dependencies were called correctly
    mock_embeddings.assert_called_once_with(["What is the fee for CS?"])
    mock_db_session.execute.assert_called_once()
    mock_llm.assert_called_once()


def test_chat_validation_empty_query(client: TestClient) -> None:
    """Verify that empty queries fail Pydantic model validation rules with 422."""
    payload = {"message": "   "}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422


def test_chat_no_context(
    client: TestClient,
    mock_db_session: AsyncMock,
    mock_embeddings: MagicMock,
    mock_llm: MagicMock,
) -> None:
    """Verify fallback behavior when similarity search returns zero matching documents."""
    # Reset database mock to return empty context list
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    # Mock LLM to return a fallback message
    mock_llm.return_value = "I do not have access to any college documents to answer this."

    payload = {"message": "What is the cutoff for college X?"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "I do not have access to any college documents to answer this."
    assert data["sources"] == []

    # Verify embeddings were still generated and database was searched
    mock_embeddings.assert_called_once_with(["What is the cutoff for college X?"])
    mock_db_session.execute.assert_called_once()
    mock_llm.assert_called_once()

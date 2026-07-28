import email.message
import urllib.error
from typing import AsyncIterator, Generator
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from fastapi.testclient import TestClient
from pypdf.errors import PdfReadError
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.main import app
from api.services.chunker import chunk_text


@pytest.fixture(autouse=True)
def mock_db_session() -> Generator[AsyncMock, None, None]:
    """Mock the FastAPI get_db dependency to avoid real DB connections."""
    mock_session = AsyncMock(spec=AsyncSession)

    # Set up mock execute results for select queries
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    async def override_get_db() -> AsyncIterator[AsyncMock]:
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    yield mock_session
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_embeddings() -> Generator[MagicMock, None, None]:
    """Mock get_embeddings calls globally to avoid calling Gemini API."""
    with patch("api.services.document_service.get_embeddings") as mock:
        # Default mock returns a list of dummy 768-dimensional float arrays
        mock.return_value = [[0.1] * 768]
        yield mock


def test_process_document_validation_invalid_extension(client: TestClient) -> None:
    # PDF references must end with .pdf
    response = client.post("/documents/process", json={"document_ref": "invalid.txt"})
    assert response.status_code == 422
    assert "must refer to a PDF file" in response.json()["detail"][0]["msg"]


def test_process_document_validation_empty_ref(client: TestClient) -> None:
    # PDF reference cannot be empty
    response = client.post("/documents/process", json={"document_ref": ""})
    assert response.status_code == 422
    assert "Document reference cannot be empty" in response.json()["detail"][0]["msg"]


@patch("api.services.document_service.os.path.exists")
def test_process_document_local_not_found(
    mock_exists: MagicMock, client: TestClient
) -> None:
    # Local file not found
    mock_exists.return_value = False
    response = client.post(
        "/documents/process", json={"document_ref": "/missing/file.pdf"}
    )
    assert response.status_code == 404
    assert "Local document file not found" in response.json()["detail"]


@patch("api.services.document_service.os.path.exists")
@patch("api.services.document_service.os.path.isdir")
def test_process_document_local_is_directory(
    mock_isdir: MagicMock, mock_exists: MagicMock, client: TestClient
) -> None:
    # Path is directory
    mock_exists.return_value = True
    mock_isdir.return_value = True
    response = client.post(
        "/documents/process", json={"document_ref": "/some/directory.pdf"}
    )
    assert response.status_code == 422
    assert "points to a directory" in response.json()["detail"]


@patch("api.services.document_service.os.path.exists")
@patch("api.services.document_service.os.path.isdir")
@patch("api.services.document_service.open", new_callable=mock_open)
@patch("api.services.pdf_extractor.pypdf.PdfReader")
def test_process_document_local_success(
    mock_pdf_reader: MagicMock,
    mock_file: MagicMock,
    mock_isdir: MagicMock,
    mock_exists: MagicMock,
    client: TestClient,
    mock_db_session: AsyncMock,
) -> None:
    # Success reading local file
    mock_exists.return_value = True
    mock_isdir.return_value = False

    # Mock file content
    mock_file.return_value.read.return_value = b"%PDF-1.4..."

    # Mock PdfReader and Page
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hello World from local PDF"
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [mock_page]
    mock_pdf_reader.return_value = mock_reader_instance

    response = client.post(
        "/documents/process", json={"document_ref": "/valid/file.pdf"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["document_ref"] == "/valid/file.pdf"
    assert body["total_chunks"] == 1
    assert body["inserted_chunks"] == 1
    assert body["skipped_chunks"] == 0
    assert body["extracted_text"] == "Hello World from local PDF"

    # Verify db calls
    assert mock_db_session.add.call_count >= 2  # Document + DocumentChunk
    assert mock_db_session.commit.call_count == 1


@patch("api.services.document_service.urllib.request.urlopen")
@patch("api.services.pdf_extractor.pypdf.PdfReader")
def test_process_document_url_success(
    mock_pdf_reader: MagicMock,
    mock_urlopen: MagicMock,
    client: TestClient,
    mock_db_session: AsyncMock,
) -> None:
    # Success downloading and parsing URL
    mock_response = MagicMock()
    mock_response.read.return_value = b"%PDF-1.4..."
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    # Mock PDF Page text
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hello World from URL PDF"
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [mock_page]
    mock_pdf_reader.return_value = mock_reader_instance

    response = client.post(
        "/documents/process", json={"document_ref": "https://example.com/file.pdf"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["document_ref"] == "https://example.com/file.pdf"
    assert body["total_chunks"] == 1
    assert body["inserted_chunks"] == 1
    assert body["extracted_text"] == "Hello World from URL PDF"

    assert mock_db_session.add.call_count >= 2
    assert mock_db_session.commit.call_count == 1


@patch("api.services.document_service.urllib.request.urlopen")
def test_process_document_url_not_found(
    mock_urlopen: MagicMock, client: TestClient
) -> None:
    # URL returns HTTPError (e.g. 404)
    mock_urlopen.side_effect = urllib.error.HTTPError(
        "https://example.com/404.pdf",
        404,
        "Not Found",
        email.message.Message(),
        None,
    )

    response = client.post(
        "/documents/process", json={"document_ref": "https://example.com/404.pdf"}
    )
    assert response.status_code == 404
    assert "HTTP status 404" in response.json()["detail"]


@patch("api.services.document_service.os.path.exists")
@patch("api.services.document_service.os.path.isdir")
@patch("api.services.document_service.open", new_callable=mock_open)
@patch("api.services.pdf_extractor.pypdf.PdfReader")
def test_process_document_corrupted_pdf(
    mock_pdf_reader: MagicMock,
    mock_file: MagicMock,
    mock_isdir: MagicMock,
    mock_exists: MagicMock,
    client: TestClient,
) -> None:
    # Corrupted PDF
    mock_exists.return_value = True
    mock_isdir.return_value = False
    mock_file.return_value.read.return_value = b"corrupted bytes"

    # Mock PdfReader to raise PdfReadError
    mock_pdf_reader.side_effect = PdfReadError("EOF marker not found")

    response = client.post(
        "/documents/process", json={"document_ref": "/corrupted/file.pdf"}
    )
    assert response.status_code == 400
    assert "Failed to parse PDF document" in response.json()["detail"]


@patch("api.services.document_service.os.path.exists")
@patch("api.services.document_service.os.path.isdir")
@patch("api.services.document_service.open", new_callable=mock_open)
@patch("api.services.pdf_extractor.pypdf.PdfReader")
def test_process_document_empty_extracted_text(
    mock_pdf_reader: MagicMock,
    mock_file: MagicMock,
    mock_isdir: MagicMock,
    mock_exists: MagicMock,
    client: TestClient,
) -> None:
    # Empty PDF (e.g., image-only PDF with no OCR or blank pages)
    mock_exists.return_value = True
    mock_isdir.return_value = False
    mock_file.return_value.read.return_value = b"%PDF-1.4..."

    # Mock PdfReader to return page with empty text
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "   "
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [mock_page]
    mock_pdf_reader.return_value = mock_reader_instance

    response = client.post(
        "/documents/process", json={"document_ref": "/empty/file.pdf"}
    )
    assert response.status_code == 422
    assert "Extracted text is empty" in response.json()["detail"]


def test_chunk_text_boundaries() -> None:
    # Test word chunk limits and overlapping
    sample_text = "one two three four five six"
    # Chunk size = 3, overlap = 1
    # Chunk 1: one two three
    # Chunk 2: three four five
    # Chunk 3: five six
    chunks = chunk_text(sample_text, chunk_size=3, overlap=1)
    assert len(chunks) == 3
    assert chunks[0]["text_content"] == "one two three"
    assert chunks[1]["text_content"] == "three four five"
    assert chunks[2]["text_content"] == "five six"
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert chunks[2]["chunk_index"] == 2
    assert "sha256" in chunks[0]


@patch("api.services.document_service.os.path.exists")
@patch("api.services.document_service.os.path.isdir")
@patch("api.services.document_service.open", new_callable=mock_open)
@patch("api.services.pdf_extractor.pypdf.PdfReader")
def test_process_document_chunk_deduplication(
    mock_pdf_reader: MagicMock,
    mock_file: MagicMock,
    mock_isdir: MagicMock,
    mock_exists: MagicMock,
    client: TestClient,
    mock_db_session: AsyncMock,
    mock_embeddings: MagicMock,
) -> None:
    # Set up mocks for success
    mock_exists.return_value = True
    mock_isdir.return_value = False
    mock_file.return_value.read.return_value = b"%PDF-1.4..."

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hello World from PDF"
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [mock_page]
    mock_pdf_reader.return_value = mock_reader_instance

    # Mock the database to return that the SHA-256 hash already exists in db
    mock_result = MagicMock()
    # Chunker calculates SHA-256 for "Hello World from PDF" which will be queried
    # We return it in the query response list to simulate it exists
    expected_hash = "dbf6fef6c434a10d8bb9a767dae8502145bace5ba256ba6eb0ad5c7502c01433"
    mock_result.scalars.return_value.all.return_value = [expected_hash]
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Override embedding list
    mock_embeddings.return_value = []

    response = client.post(
        "/documents/process", json={"document_ref": "/dedup/file.pdf"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_chunks"] == 1
    assert body["inserted_chunks"] == 0
    assert body["skipped_chunks"] == 1

    # Verify that get_embeddings was NOT called since there were 0 new chunks
    mock_embeddings.assert_not_called()

import email.message
import urllib.error
from unittest.mock import MagicMock, mock_open, patch

from fastapi.testclient import TestClient
from pypdf.errors import PdfReadError


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
    assert body["extracted_text"] == "Hello World from local PDF"


@patch("api.services.document_service.urllib.request.urlopen")
@patch("api.services.pdf_extractor.pypdf.PdfReader")
def test_process_document_url_success(
    mock_pdf_reader: MagicMock, mock_urlopen: MagicMock, client: TestClient
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
    assert body["extracted_text"] == "Hello World from URL PDF"


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

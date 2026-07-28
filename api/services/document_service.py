import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

from api.core.exceptions import (
    DocumentNotFoundError,
    InvalidDocumentRefError,
)
from api.core.logging import get_logger
from api.services.pdf_extractor import extract_text_from_pdf_bytes

logger = get_logger(__name__)


def _is_url(ref: str) -> bool:
    """Helper to check if a reference string is a valid URL."""
    try:
        result = urlparse(ref)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def _fetch_from_url(url: str) -> bytes:
    """Download PDF bytes from a remote URL with proper timeouts and headers."""
    logger.debug("fetching_document_from_url", url=url)
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124"
                )
            },
        )
        # Using a 10-second timeout to prevent blocking indefinitely
        with urllib.request.urlopen(req, timeout=10) as response:
            return bytes(response.read())
    except urllib.error.HTTPError as e:
        logger.error(
            "url_fetch_http_error", url=url, status_code=e.code, reason=e.reason
        )
        raise DocumentNotFoundError(
            f"Failed to fetch document from URL. HTTP status {e.code}: {e.reason}"
        ) from e
    except urllib.error.URLError as e:
        logger.error("url_fetch_url_error", url=url, reason=str(e.reason))
        raise DocumentNotFoundError(
            f"Failed to fetch document from URL. Network error: {e.reason}"
        ) from e
    except TimeoutError as e:
        logger.error("url_fetch_timeout", url=url)
        raise DocumentNotFoundError(
            "Failed to fetch document from URL. Request timed out."
        ) from e
    except Exception as e:
        logger.error("url_fetch_unexpected_error", url=url, error=str(e))
        raise DocumentNotFoundError(
            f"Failed to fetch document from URL: {str(e)}"
        ) from e


def _fetch_from_local_path(path: str) -> bytes:
    """Read PDF bytes from a local file path."""
    logger.debug("reading_document_from_local_path", path=path)

    # Clean the path to avoid directory traversal or standard issues
    abs_path = os.path.abspath(path)

    if not os.path.exists(abs_path):
        logger.error("local_file_not_found", path=abs_path)
        raise DocumentNotFoundError(f"Local document file not found at path: {path}")

    if os.path.isdir(abs_path):
        logger.error("local_path_is_directory", path=abs_path)
        raise InvalidDocumentRefError(
            f"Document reference path points to a directory: {path}"
        )

    try:
        with open(abs_path, "rb") as f:
            return f.read()
    except PermissionError as e:
        logger.error("local_file_permission_denied", path=abs_path, error=str(e))
        raise DocumentNotFoundError(
            f"Permission denied reading local document: {path}"
        ) from e
    except Exception as e:
        logger.error("local_file_read_error", path=abs_path, error=str(e))
        raise DocumentNotFoundError(
            f"Failed to read local document file: {str(e)}"
        ) from e


def process_document(document_ref: str) -> str:
    """Fetch PDF document from reference, extract its text, log, and return it.

    Raises:
        InvalidDocumentRefError: If reference is malformed.
        DocumentNotFoundError: If the file or URL is missing/unreachable.
        CorruptedDocumentError: If PDF fails to parse.
        EmptyDocumentTextError: If no text was extracted.
    """
    logger.info("processing_document_start", document_ref=document_ref)

    if _is_url(document_ref):
        pdf_bytes = _fetch_from_url(document_ref)
    else:
        pdf_bytes = _fetch_from_local_path(document_ref)

    extracted_text = extract_text_from_pdf_bytes(pdf_bytes)

    # Structured logging of extracted text for verification
    preview_len = min(200, len(extracted_text))
    logger.info(
        "document_processing_success",
        document_ref=document_ref,
        extracted_length=len(extracted_text),
        text_preview=extracted_text[:preview_len]
        + ("..." if len(extracted_text) > preview_len else ""),
        full_text=extracted_text,
    )

    return extracted_text

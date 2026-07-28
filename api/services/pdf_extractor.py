import io

import pypdf
from pypdf.errors import PdfReadError

from api.core.exceptions import CorruptedDocumentError, EmptyDocumentTextError
from api.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract all readable text from the PDF bytes.

    Raises:
        CorruptedDocumentError: If the PDF is corrupted or cannot be parsed.
        EmptyDocumentTextError: If the PDF contains no extractable text.
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        logger.debug("pdf_opened_successfully", page_count=num_pages)

        extracted_pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_pages.append(text)

        full_text = "\n".join(extracted_pages).strip()
        if not full_text:
            raise EmptyDocumentTextError(
                "Extracted text is empty or the PDF contains no readable text"
            )

        return full_text

    except (PdfReadError, Exception) as e:
        if isinstance(e, EmptyDocumentTextError):
            raise e
        logger.error("pdf_extraction_failed", error=str(e))
        raise CorruptedDocumentError(f"Failed to parse PDF document: {str(e)}") from e

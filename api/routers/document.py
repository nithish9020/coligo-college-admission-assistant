from fastapi import APIRouter, status

from api.core.logging import get_logger
from api.schemas import DocumentProcessRequest, DocumentProcessResponse
from api.services import process_document

router = APIRouter(prefix="/documents", tags=["Document Ingestion"])
logger = get_logger(__name__)


@router.post(
    "/process",
    response_model=DocumentProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process PDF Document",
)
async def process_document_endpoint(
    request: DocumentProcessRequest,
) -> DocumentProcessResponse:
    """Process a PDF document by reference (local path or URL) and return its
    extracted text.

    - **document_ref**: File path or URL to the target PDF document.
    """
    logger.info(
        "process_document_endpoint_requested", document_ref=request.document_ref
    )
    extracted_text = process_document(request.document_ref)
    return DocumentProcessResponse(
        document_ref=request.document_ref,
        extracted_text=extracted_text,
    )

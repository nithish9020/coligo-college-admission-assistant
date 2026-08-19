from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.logging import get_logger
from api.schemas.document import (
    DocumentItemResponse,
    DocumentListResponse,
    DocumentProcessRequest,
    DocumentProcessResponse,
    ScrapeRequest,
)
from api.services.document_service import (
    delete_document,
    list_documents,
    process_document,
)
from api.services.web_scraper import scrape_college_urls_to_file

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
    db: AsyncSession = Depends(get_db),
) -> DocumentProcessResponse:
    """Process a PDF document by reference (local path or URL) and store chunks."""
    logger.info(
        "process_document_endpoint_requested", document_ref=request.document_ref
    )

    (
        extracted_text,
        total_chunks,
        inserted_chunks,
        skipped_chunks,
    ) = await process_document(db, request.document_ref)

    return DocumentProcessResponse(
        document_ref=request.document_ref,
        total_chunks=total_chunks,
        inserted_chunks=inserted_chunks,
        skipped_chunks=skipped_chunks,
        extracted_text=extracted_text,
    )


@router.post(
    "/scrape",
    response_model=DocumentProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Scrape College Websites & Ingest",
)
async def scrape_college_endpoint(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentProcessResponse:
    """Scrape web pages for a college, combine extracted text, and store chunks."""
    logger.info(
        "scrape_college_requested",
        college_name=request.college_name,
        url_count=len(request.urls),
    )

    try:
        scraped_file_path = await scrape_college_urls_to_file(
            request.urls, request.college_name
        )
    except Exception as e:
        logger.error("scrape_college_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape college URLs: {str(e)}",
        ) from e

    (
        extracted_text,
        total_chunks,
        inserted_chunks,
        skipped_chunks,
    ) = await process_document(db, scraped_file_path)

    return DocumentProcessResponse(
        document_ref=scraped_file_path,
        total_chunks=total_chunks,
        inserted_chunks=inserted_chunks,
        skipped_chunks=skipped_chunks,
        extracted_text=extracted_text,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Ingested Documents",
)
async def list_documents_endpoint(
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List all ingested documents and chunk counts for the Admin Portal."""
    docs = await list_documents(db)
    items = [DocumentItemResponse(**doc) for doc in docs]
    return DocumentListResponse(total=len(items), documents=items)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Ingested Document",
)
async def delete_document_endpoint(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an ingested document and its owned chunks."""
    success = await delete_document(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return {"status": "deleted", "document_id": document_id}

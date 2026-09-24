import os
import urllib.error
import urllib.request
from typing import Tuple
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.exceptions import (
    DocumentNotFoundError,
    InvalidDocumentRefError,
)
from api.core.logging import get_logger
from api.models import Document, DocumentChunk
from api.services.chunker import chunk_text
from api.services.embedding_service import get_embeddings
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


async def process_document(
    db: AsyncSession, document_ref: str
) -> Tuple[str, int, int, int]:
    """Fetch PDF document, extract text, chunk it, embed it, and store in database.

    Handles deduplication of chunks globally: if a chunk SHA-256 already exists,
    it skips storing that chunk again and avoids generating its embedding.

    Returns:
        Tuple of (extracted_text, total_chunks, inserted_chunks, skipped_chunks)
    """
    logger.info("processing_document_start", document_ref=document_ref)

    if _is_url(document_ref):
        doc_bytes = _fetch_from_url(document_ref)
    else:
        doc_bytes = _fetch_from_local_path(document_ref)

    if document_ref.endswith(".txt"):
        extracted_text = doc_bytes.decode("utf-8", errors="ignore")
    else:
        extracted_text = extract_text_from_pdf_bytes(doc_bytes)

    # Structured logging of extracted text for verification
    preview_len = min(200, len(extracted_text))
    logger.info(
        "document_text_extracted_for_db",
        document_ref=document_ref,
        extracted_length=len(extracted_text),
        text_preview=extracted_text[:preview_len]
        + ("..." if len(extracted_text) > preview_len else ""),
    )

    # 1. Split text into chunks
    chunks = chunk_text(
        extracted_text,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )
    total_chunks = len(chunks)

    # 2. Manage existing document references (re-processing scenario)
    existing_doc_query = select(Document).where(Document.document_ref == document_ref)
    existing_doc = (await db.execute(existing_doc_query)).scalars().first()
    if existing_doc:
        logger.info(
            "document_reprocessing_deleting_old_record", document_ref=document_ref
        )
        await db.delete(existing_doc)
        await db.flush()

    # 3. Create new Document record
    db_document = Document(document_ref=document_ref)
    db.add(db_document)
    await db.flush()  # Populates db_document.id

    # 4. Smart Deduplication: Reuse existing embeddings by sha256 to save API calls
    # while ensuring every document owns its own DocumentChunk rows.
    all_hashes = [c["sha256"] for c in chunks]
    existing_embedding_map = {}
    if all_hashes:
        existing_chunks_query = select(
            DocumentChunk.sha256, DocumentChunk.embedding
        ).where(DocumentChunk.sha256.in_(all_hashes))
        result = await db.execute(existing_chunks_query)
        for sha256_hash, emb in result.all():
            if sha256_hash not in existing_embedding_map:
                existing_embedding_map[sha256_hash] = emb

    # 5. Fetch Embeddings only for brand new hashes to save cost/time
    missing_chunks = [c for c in chunks if c["sha256"] not in existing_embedding_map]
    if missing_chunks:
        texts_to_embed = [c["text_content"] for c in missing_chunks]
        new_embeddings = await get_embeddings(texts_to_embed)
        for c, emb in zip(missing_chunks, new_embeddings, strict=False):
            existing_embedding_map[c["sha256"]] = emb

    # 6. Add all chunks for this document using the embedding map
    for chunk_data in chunks:
        db_chunk = DocumentChunk(
            document_id=db_document.id,
            chunk_index=chunk_data["chunk_index"],
            text_content=chunk_data["text_content"],
            sha256=chunk_data["sha256"],
            embedding=existing_embedding_map[chunk_data["sha256"]],
        )
        db.add(db_chunk)

    # Commit all changes to the database
    await db.commit()

    reused_embeddings_count = total_chunks - len(missing_chunks)
    logger.info(
        "document_processing_db_success",
        document_ref=document_ref,
        total_chunks=total_chunks,
        inserted_chunks=total_chunks,
        reused_embeddings_count=reused_embeddings_count,
    )

    return (
        extracted_text,
        total_chunks,
        total_chunks,
        reused_embeddings_count,
    )


async def list_documents(db: AsyncSession) -> list[dict]:
    """List all ingested documents with chunk counts for the Admin Portal."""
    stmt = select(Document).order_by(Document.created_at.desc())
    documents = (await db.execute(stmt)).scalars().all()

    result = []
    for doc in documents:
        chunk_count_stmt = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == doc.id
        )
        chunk_count = (await db.execute(chunk_count_stmt)).scalar() or 0
        result.append(
            {
                "id": doc.id,
                "document_ref": doc.document_ref,
                "chunk_count": chunk_count,
                "created_at": doc.created_at.isoformat(),
            }
        )
    return result


async def delete_document(db: AsyncSession, document_id: int) -> bool:
    """Delete a document and its owned chunks safely."""
    doc = await db.get(Document, document_id)
    if not doc:
        return False

    await db.delete(doc)
    await db.commit()
    logger.info("document_deleted", document_id=document_id)
    return True

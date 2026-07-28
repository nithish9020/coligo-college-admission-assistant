import hashlib
from typing import Any, Dict, List

from api.core.logging import get_logger

logger = get_logger(__name__)


def chunk_text(
    text: str, chunk_size: int = 512, overlap: int = 50
) -> List[Dict[str, Any]]:
    """Splits input text into chunks based on word limits with a sliding overlap.

    Returns a list of dicts:
    [
        {
            "chunk_index": int,
            "text_content": str,
            "sha256": str
        },
        ...
    ]
    """
    logger.debug(
        "starting_text_chunking",
        text_length=len(text),
        chunk_size=chunk_size,
        overlap=overlap,
    )

    words = text.split()
    if not words:
        logger.debug("chunking_aborted_empty_text")
        return []

    chunks: List[Dict[str, Any]] = []
    i = 0
    chunk_index = 0

    # Ensure overlap is strictly less than chunk_size to avoid infinite loops
    if overlap >= chunk_size:
        logger.warning(
            "overlap_larger_than_chunk_size",
            chunk_size=chunk_size,
            overlap=overlap,
        )
        overlap = max(0, chunk_size - 1)

    step = chunk_size - overlap

    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunk_text_content = " ".join(chunk_words).strip()

        if chunk_text_content:
            # Generate SHA-256 hash of the text content for deduplication
            sha256_hash = hashlib.sha256(chunk_text_content.encode("utf-8")).hexdigest()
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "text_content": chunk_text_content,
                    "sha256": sha256_hash,
                }
            )
            chunk_index += 1

        i += step

    logger.debug("chunking_completed", total_chunks=len(chunks))
    return chunks

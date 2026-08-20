import asyncio
from typing import List

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Fetch text embeddings using Google Gemini API."""
    if not settings.GEMINI_API_KEY:
        logger.error("gemini_api_key_missing_for_embeddings")
        raise DocumentProcessingError(
            "GEMINI_API_KEY is not configured in the application environment."
        )

    genai.configure(api_key=settings.GEMINI_API_KEY)

    all_embeddings: List[List[float]] = []

    # Process sequentially or in batches depending on rate limits.
    # Google's embed_content accepts a list of strings natively for batching.
    batch_size = 100  # Gemini allows up to 100 per request

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.debug(
            "sending_gemini_embedding_batch",
            batch_index=i // batch_size,
            batch_size=len(batch),
        )

        for attempt in range(5):
            try:
                # Use synchronous API wrapped in asyncio.to_thread
                def _fetch_embeddings(current_batch: List[str]):
                    return genai.embed_content(
                        model=settings.GEMINI_EMBEDDING_MODEL,
                        content=current_batch,
                        task_type="retrieval_document",
                    )

                response = await asyncio.to_thread(_fetch_embeddings, batch)
                embeddings = response.get("embedding", [])

                if len(embeddings) != len(batch):
                    raise DocumentProcessingError(
                        f"Mismatch: expected {len(batch)}, got {len(embeddings)}"
                    )

                all_embeddings.extend(embeddings)
                break

            except google_exceptions.ResourceExhausted:
                wait_sec = 2**attempt + 2
                logger.warning(
                    "gemini_embedding_rate_limited_retrying",
                    attempt=attempt + 1,
                    wait_seconds=wait_sec,
                )
                await asyncio.sleep(wait_sec)

            except Exception as e:
                if attempt == 4:
                    logger.error(
                        "gemini_embedding_api_failed",
                        error=str(e),
                    )
                    raise DocumentProcessingError(
                        f"Failed to generate embeddings from Gemini API: {str(e)}"
                    ) from e
                await asyncio.sleep(2)

        if i + batch_size < len(texts):
            await asyncio.sleep(0.5)

    return all_embeddings

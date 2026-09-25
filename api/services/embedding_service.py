import asyncio
from typing import List

from google import genai
from google.genai import errors as genai_errors

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)

# Module-level singleton — genai.Client is stateless and thread-safe.
_embed_client: genai.Client | None = None


def _get_embed_client() -> genai.Client:
    """Return (and lazily create) the shared Gemini embedding client."""
    global _embed_client
    if _embed_client is None:
        if not settings.GEMINI_API_KEY:
            raise DocumentProcessingError(
                "GEMINI_API_KEY is not configured in the application environment."
            )
        _embed_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _embed_client


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Fetch text embeddings using Google Gemini API (google-genai SDK)."""
    client = _get_embed_client()
    all_embeddings: List[List[float]] = []

    # google-genai embed_content supports batches natively.
    # We process in chunks of 20 to stay within API limits.
    batch_size = 20

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.debug(
            "sending_gemini_embedding_batch",
            batch_index=i // batch_size,
            batch_size=len(batch),
        )

        for attempt in range(5):
            try:

                def _fetch_embeddings(
                    current_client: genai.Client, current_batch: List[str]
                ) -> List[List[float]]:
                    result = current_client.models.embed_content(
                        model=settings.GEMINI_EMBEDDING_MODEL,
                        contents=current_batch,  # type: ignore[arg-type]
                        config={"output_dimensionality": settings.EMBEDDING_DIMENSION},
                    )
                    embeddings = result.embeddings or []
                    if not embeddings:
                        raise DocumentProcessingError(
                            "Gemini embedding API returned no embedding for a chunk."
                        )

                    results = []
                    for emb in embeddings:
                        results.append(list(emb.values or []))
                    return results

                batch_embeddings = await asyncio.to_thread(
                    _fetch_embeddings, client, batch
                )

                if len(batch_embeddings) != len(batch):
                    raise DocumentProcessingError(
                        f"Mismatch: expected {len(batch)}, got {len(batch_embeddings)}"
                    )

                all_embeddings.extend(batch_embeddings)
                break

            except genai_errors.ClientError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt >= 5:
                        logger.error("gemini_embedding_api_rate_limit_exhausted")
                        raise DocumentProcessingError(
                            "Gemini API rate limit exhausted after retries."
                        ) from e
                    wait_sec = (attempt + 1) * 12
                    logger.warning(
                        "gemini_embedding_rate_limited_retrying",
                        attempt=attempt + 1,
                        wait_seconds=wait_sec,
                    )
                    await asyncio.sleep(wait_sec)
                else:
                    logger.error("gemini_embedding_api_failed", error=str(e))
                    raise DocumentProcessingError(
                        f"Gemini embedding API error: {str(e)}"
                    ) from e

            except Exception as e:
                if attempt == 4:
                    logger.error("gemini_embedding_api_failed", error=str(e))
                    raise DocumentProcessingError(
                        f"Failed to generate embeddings from Gemini API: {str(e)}"
                    ) from e
                await asyncio.sleep(2)

        if i + batch_size < len(texts):
            await asyncio.sleep(0.5)

    return all_embeddings

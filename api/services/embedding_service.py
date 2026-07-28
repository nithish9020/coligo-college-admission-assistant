from typing import List

import httpx

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Fetch text embeddings using Google Gemini batchEmbedContents API.

    Performs HTTP POST requests asynchronously and splits input into batches
    of 100 to meet API requirements.

    Raises:
        DocumentProcessingError: If API key is missing or HTTP request fails.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("gemini_api_key_missing")
        raise DocumentProcessingError(
            "GEMINI_API_KEY is not configured in the application environment."
        )

    # Base Gemini API endpoint URL
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_EMBEDDING_MODEL}:batchEmbedContents"
        f"?key={settings.GEMINI_API_KEY}"
    )

    batch_size = 100
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.debug(
            "sending_embedding_batch",
            batch_index=i // batch_size,
            batch_size=len(batch),
        )

        # Construct batch request body matching Gemini API specification
        requests_payload = []
        for text in batch:
            requests_payload.append(
                {
                    "model": f"models/{settings.GEMINI_EMBEDDING_MODEL}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": 768,
                }
            )

        payload = {"requests": requests_payload}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)

            if response.status_code != 200:
                logger.error(
                    "gemini_embedding_api_failed",
                    status_code=response.status_code,
                    body=response.text,
                )
                raise DocumentProcessingError(
                    "Gemini API returned error status "
                    f"{response.status_code}: {response.text}"
                )

            response_data = response.json()
            embeddings_list = response_data.get("embeddings", [])

            if len(embeddings_list) != len(batch):
                raise DocumentProcessingError(
                    "Gemini API returned mismatching embedding count: "
                    f"expected {len(batch)}, got {len(embeddings_list)}"
                )

            for item in embeddings_list:
                all_embeddings.append(item["values"])

        except httpx.RequestError as e:
            logger.error("gemini_embedding_request_error", error=str(e))
            raise DocumentProcessingError(
                f"Network request to Gemini API failed: {str(e)}"
            ) from e
        except Exception as e:
            if isinstance(e, DocumentProcessingError):
                raise e
            logger.error("gemini_embedding_unexpected_error", error=str(e))
            raise DocumentProcessingError(
                f"Failed to generate document embeddings: {str(e)}"
            ) from e

    return all_embeddings

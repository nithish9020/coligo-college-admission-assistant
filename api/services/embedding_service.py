import asyncio
from typing import List

import httpx

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)


async def _send_single_nvidia_embedding_batch(
    url: str, headers: dict, batch: List[str]
) -> List[List[float]]:
    """Send a batch of text strings to NVIDIA NIM Embeddings API."""
    payload = {
        "input": batch,
        "model": settings.NVIDIA_EMBEDDING_MODEL,
        "input_type": "query",
        "truncate": "END",
    }

    for attempt in range(5):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=45.0
                )

            if response.status_code == 429:
                wait_sec = 2**attempt + 2
                logger.warning(
                    "nvidia_embedding_rate_limited_retrying",
                    attempt=attempt + 1,
                    wait_seconds=wait_sec,
                )
                await asyncio.sleep(wait_sec)
                continue

            if response.status_code != 200:
                logger.error(
                    "nvidia_embedding_api_failed",
                    status_code=response.status_code,
                    body=response.text,
                )
                raise DocumentProcessingError(
                    f"NVIDIA API error {response.status_code}: {response.text}"
                )

            response_data = response.json()
            data_items = response_data.get("data", [])

            if len(data_items) != len(batch):
                raise DocumentProcessingError(
                    f"Mismatch: expected {len(batch)}, got {len(data_items)}"
                )

            # Sort by index to maintain input order and slice to 768 dimensions
            sorted_items = sorted(data_items, key=lambda item: item.get("index", 0))
            return [item["embedding"][:768] for item in sorted_items]

        except httpx.RequestError as e:
            if attempt == 4:
                raise DocumentProcessingError(
                    f"Network request to NVIDIA Embeddings API failed: {str(e)}"
                ) from e
            await asyncio.sleep(2)

    raise DocumentProcessingError(
        "Failed to generate embeddings from NVIDIA NIM API after retries"
    )


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Fetch text embeddings using NVIDIA NIM Embeddings API."""
    if not settings.NVIDIA_API_KEY:
        logger.error("nvidia_api_key_missing_for_embeddings")
        raise DocumentProcessingError(
            "NVIDIA_API_KEY is not configured in the application environment."
        )

    url = "https://integrate.api.nvidia.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    batch_size = 10
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.debug(
            "sending_nvidia_embedding_batch",
            batch_index=i // batch_size,
            batch_size=len(batch),
        )
        batch_embeddings = await _send_single_nvidia_embedding_batch(
            url, headers, batch
        )
        all_embeddings.extend(batch_embeddings)
        if i + batch_size < len(texts):
            await asyncio.sleep(0.5)

    return all_embeddings

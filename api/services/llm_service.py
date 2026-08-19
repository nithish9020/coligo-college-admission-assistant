import httpx

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)


async def generate_response_from_llm(prompt: str) -> str:
    """Generate response using NVIDIA NIM API (OpenAI compatible endpoint).

    Model: openai/gpt-oss-120b (https://build.nvidia.com/openai/gpt-oss-120b)
    """
    if not settings.NVIDIA_API_KEY:
        logger.error("nvidia_api_key_missing_for_llm")
        raise DocumentProcessingError(
            "NVIDIA_API_KEY is not configured in the application environment."
        )

    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.NVIDIA_LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "top_p": 1,
        "max_tokens": 1024,
        "stream": False,
    }

    logger.debug("sending_prompt_to_nvidia_llm", model=settings.NVIDIA_LLM_MODEL)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=60.0
            )

        if response.status_code != 200:
            logger.error(
                "nvidia_llm_api_failed",
                status_code=response.status_code,
                body=response.text,
            )
            raise DocumentProcessingError(
                f"NVIDIA NIM API error status {response.status_code}: {response.text}"
            )

        response_data = response.json()
        choices = response_data.get("choices", [])
        if not choices:
            raise DocumentProcessingError("NVIDIA NIM API returned no choices.")

        message = choices[0].get("message", {})
        content = message.get("content", "")
        return str(content).strip()

    except httpx.RequestError as e:
        logger.error("nvidia_llm_request_error", error=str(e))
        raise DocumentProcessingError(
            f"Network request to NVIDIA NIM API failed: {str(e)}"
        ) from e

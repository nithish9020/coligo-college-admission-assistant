import httpx

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)


async def generate_response_from_llm(prompt: str) -> str:
    """Send prompt to the Google Gemini-1.5-Flash API and return generated content.

    Raises:
        DocumentProcessingError: If API key is missing or HTTP request fails.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("gemini_api_key_missing_for_llm")
        raise DocumentProcessingError(
            "GEMINI_API_KEY is not configured in the application environment."
        )

    # Base Gemini API endpoint URL for content generation
    url = (
        "https://generativelanguage.googleapis.com/v1/models/"
        f"{settings.GEMINI_LLM_MODEL}:generateContent"
        f"?key={settings.GEMINI_API_KEY}"
    )

    # Construct generation payload matching Gemini API specification
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    logger.debug("sending_prompt_to_llm", model=settings.GEMINI_LLM_MODEL)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)

        if response.status_code != 200:
            logger.error(
                "gemini_llm_api_failed",
                status_code=response.status_code,
                body=response.text,
            )
            raise DocumentProcessingError(
                "Gemini LLM API returned error status "
                f"{response.status_code}: {response.text}"
            )

        response_data = response.json()
        candidates = response_data.get("candidates", [])

        if not candidates:
            logger.warning("gemini_llm_returned_no_candidates")
            raise DocumentProcessingError("Gemini LLM API returned no candidates.")

        # Extract generated response text content
        generated_text = str(
            candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        )

        return generated_text.strip()

    except httpx.RequestError as e:
        logger.error("gemini_llm_request_error", error=str(e))
        raise DocumentProcessingError(
            f"Network request to Gemini LLM API failed: {str(e)}"
        ) from e
    except Exception as e:
        if isinstance(e, DocumentProcessingError):
            raise e
        logger.error("gemini_llm_unexpected_error", error=str(e))
        raise DocumentProcessingError(
            f"Failed to generate LLM response: {str(e)}"
        ) from e

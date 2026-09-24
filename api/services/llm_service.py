import asyncio

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)

# Module-level singleton — genai.Client is stateless and thread-safe.
_llm_client: genai.Client | None = None


def _get_llm_client() -> genai.Client:
    """Return (and lazily create) the shared Gemini LLM client."""
    global _llm_client
    if _llm_client is None:
        if not settings.GEMINI_API_KEY:
            raise DocumentProcessingError(
                "GEMINI_API_KEY is not configured in the application environment."
            )
        _llm_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _llm_client


async def generate_response_from_llm(prompt: str) -> str:
    """Generate response using Google Gemini API (google-genai SDK)."""
    client = _get_llm_client()

    logger.debug("sending_prompt_to_gemini_llm", model=settings.GEMINI_MODEL)
    for attempt in range(3):
        try:

            def _generate(current_client: genai.Client) -> str:
                response = current_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.2,
                        top_p=1.0,
                        max_output_tokens=1024,
                    ),
                )
                return response.text or ""

            text = await asyncio.to_thread(_generate, client)

            if text:
                return text.strip()
            else:
                raise DocumentProcessingError("Gemini API returned an empty response.")

        except genai_errors.ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logger.warning("gemini_llm_rate_limited_retrying", attempt=attempt + 1)
                await asyncio.sleep(2.0 ** (attempt + 1))
            else:
                raise DocumentProcessingError(f"Gemini API error: {str(e)}") from e

        except Exception as e:
            logger.warning(
                "gemini_llm_request_error_retrying", attempt=attempt + 1, error=str(e)
            )
            if attempt == 2:
                raise DocumentProcessingError(
                    f"Request to Gemini API failed: {str(e)}"
                ) from e
            await asyncio.sleep(2.0)

    raise DocumentProcessingError("Failed to generate response from Gemini API")

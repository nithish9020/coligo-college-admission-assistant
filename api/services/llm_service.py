import asyncio

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)


async def generate_response_from_llm(prompt: str) -> str:
    """Generate response using Google Gemini API."""
    if not settings.GEMINI_API_KEY:
        logger.error("gemini_api_key_missing_for_llm")
        raise DocumentProcessingError(
            "GEMINI_API_KEY is not configured in the application environment."
        )

    genai.configure(api_key=settings.GEMINI_API_KEY)

    logger.debug("sending_prompt_to_gemini_llm", model=settings.GEMINI_MODEL)
    for attempt in range(3):
        try:

            def _generate():
                model = genai.GenerativeModel(settings.GEMINI_MODEL)
                return model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=1.0,
                        max_output_tokens=1024,
                    ),
                )

            response = await asyncio.to_thread(_generate)

            if response.text:
                return str(response.text).strip()
            else:
                raise DocumentProcessingError("Gemini API returned an empty response.")

        except google_exceptions.ResourceExhausted:
            logger.warning("gemini_llm_rate_limited_retrying", attempt=attempt + 1)
            await asyncio.sleep(2.0 ** (attempt + 1))

        except Exception as e:
            logger.warning(
                "gemini_llm_request_error_retrying", attempt=attempt + 1, error=str(e)
            )
            if attempt == 2:
                raise DocumentProcessingError(
                    f"Network request to Gemini API failed: {str(e)}"
                ) from e
            await asyncio.sleep(2.0)

    raise DocumentProcessingError("Failed to generate response from Gemini API")

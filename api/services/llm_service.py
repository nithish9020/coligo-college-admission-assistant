import asyncio
from typing import Any

from openai import AsyncOpenAI

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)

# Module-level singleton — genai.Client is stateless and thread-safe.
_gemini_client: Any | None = None


def _get_gemini_client() -> Any:
    """Return (and lazily create) the shared Gemini LLM client."""
    global _gemini_client
    if _gemini_client is None:
        if not settings.GEMINI_API_KEY:
            raise DocumentProcessingError(
                "GEMINI_API_KEY is not configured in the application environment."
            )
        from google import genai

        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


def _resolve_openai_compatible_config() -> tuple[str, str, str | None]:
    """Resolve (api_key, model, base_url) based on LLM_PROVIDER."""
    provider = (settings.LLM_PROVIDER or "gemini").lower()
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str | None = None

    if provider == "groq":
        api_key = (
            settings.GROQ_API_KEY
            or settings.LLM_API_KEY
            or settings.OPENAI_API_KEY
            or ""
        )
        model = settings.LLM_MODEL or "llama-3.3-70b-versatile"
        base_url = settings.LLM_BASE_URL or "https://api.groq.com/openai/v1"
    elif provider == "deepseek":
        api_key = (
            settings.DEEPSEEK_API_KEY
            or settings.LLM_API_KEY
            or settings.OPENAI_API_KEY
            or ""
        )
        model = settings.LLM_MODEL or "deepseek-chat"
        base_url = settings.LLM_BASE_URL or "https://api.deepseek.com/v1"
    elif provider == "ollama":
        api_key = settings.LLM_API_KEY or "ollama"
        model = settings.LLM_MODEL or "llama3.2:3b"
        base_url = settings.LLM_BASE_URL or "http://localhost:11434/v1"
    elif provider == "openai":
        api_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY or ""
        model = settings.LLM_MODEL or settings.OPENAI_MODEL or "gpt-4o-mini"
        base_url = settings.LLM_BASE_URL
    else:  # custom / openrouter
        api_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY or ""
        model = settings.LLM_MODEL or "gpt-4o-mini"
        base_url = settings.LLM_BASE_URL

    if not api_key and provider != "ollama":
        raise DocumentProcessingError(
            f"API key for LLM provider '{provider}' is not configured "
            f"(set {provider.upper()}_API_KEY or LLM_API_KEY in .env)."
        )

    return api_key, model, base_url


async def _generate_with_openai_compatible(prompt: str) -> str:
    """Generate completions using an OpenAI-compatible endpoint.

    Supports Groq, OpenAI, DeepSeek, Ollama, OpenRouter.
    """
    api_key, model, base_url = _resolve_openai_compatible_config()
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    logger.debug(
        "sending_prompt_to_openai_compatible_llm",
        provider=settings.LLM_PROVIDER,
        model=model,
    )

    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
            )
            text = response.choices[0].message.content or ""
            if text:
                return text.strip()
            raise DocumentProcessingError("LLM returned an empty response.")
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                logger.warning("llm_rate_limited_retrying", attempt=attempt + 1)
                await asyncio.sleep(2.0 ** (attempt + 1))
            else:
                logger.warning(
                    "llm_request_error_retrying", attempt=attempt + 1, error=str(e)
                )
                if attempt == 2:
                    raise DocumentProcessingError(
                        f"Request to LLM provider '{settings.LLM_PROVIDER}' "
                        f"failed: {str(e)}"
                    ) from e
                await asyncio.sleep(2.0)

    raise DocumentProcessingError(
        f"Failed to generate response from provider '{settings.LLM_PROVIDER}'"
    )


async def _generate_with_gemini(prompt: str) -> str:
    """Generate response using Google Gemini API (google-genai SDK)."""
    from google.genai import errors as genai_errors
    from google.genai import types as genai_types

    client = _get_gemini_client()
    logger.debug("sending_prompt_to_gemini_llm", model=settings.GEMINI_MODEL)
    for attempt in range(3):
        try:

            def _generate(current_client: Any) -> str:
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


async def generate_response_from_llm(prompt: str) -> str:
    """Generate response using configured provider (Groq, Gemini, OpenAI, Ollama)."""
    provider = (settings.LLM_PROVIDER or "gemini").lower()

    # Fallback to Gemini if Groq is selected but no key is configured
    if provider == "groq" and not (
        settings.GROQ_API_KEY or settings.LLM_API_KEY or settings.OPENAI_API_KEY
    ):
        if settings.GEMINI_API_KEY:
            logger.warning(
                "groq_api_key_missing_falling_back_to_gemini",
                hint="Set GROQ_API_KEY in .env to use Groq LPU acceleration",
            )
            return await _generate_with_gemini(prompt)

    if provider == "gemini":
        return await _generate_with_gemini(prompt)
    return await _generate_with_openai_compatible(prompt)

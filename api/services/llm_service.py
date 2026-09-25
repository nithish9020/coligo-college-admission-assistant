import asyncio
from collections.abc import AsyncIterator
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


def _resolve_openai_compatible_config(
    provider_override: str | None = None,
) -> tuple[str, str, str | None]:
    """Resolve (api_key, model, base_url) based on LLM_PROVIDER or override."""
    provider = (provider_override or settings.LLM_PROVIDER or "gemini").lower()
    if provider_override is None and provider == "gemini" and settings.GROQ_API_KEY:
        provider = "groq"

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
        model = settings.LLM_MODEL or "openai/gpt-oss-120b"
        if not model or "gemini" in model.lower() or "llama-3.3" in model.lower():
            model = "openai/gpt-oss-120b"
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


async def _generate_with_openai_compatible(
    prompt: str, provider_override: str | None = None
) -> str:
    """Generate completions using an OpenAI-compatible endpoint with retries.

    Supports Groq, OpenAI, DeepSeek, Ollama, OpenRouter.
    """
    api_key, model, base_url = _resolve_openai_compatible_config(provider_override)
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    active_provider = provider_override or settings.LLM_PROVIDER
    logger.debug(
        "sending_prompt_to_openai_compatible_llm",
        provider=active_provider,
        model=model,
    )

    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
            )
            text = response.choices[0].message.content or ""
            if text and text.strip():
                return text.strip()
            raise DocumentProcessingError("LLM returned an empty response.")
        except Exception as e:
            err_str = str(e)
            is_transient = any(
                token in err_str
                for token in ("429", "500", "502", "503", "504", "rate", "overloaded")
            )
            if is_transient and attempt == 0:
                logger.warning(
                    "openai_compatible_transient_error_retrying",
                    attempt=1,
                    error=err_str,
                )
                await asyncio.sleep(2.0)
                continue
            if attempt == 1:
                raise DocumentProcessingError(
                    f"Request to LLM provider '{active_provider}' failed: {err_str}"
                ) from e
            await asyncio.sleep(1.0)

    raise DocumentProcessingError(
        f"Failed to generate response from provider '{active_provider}'"
    )


async def _generate_with_gemini(
    prompt: str, candidate_models: list[str] | None = None
) -> str:
    """Generate response using Google Gemini API with multi-model fallback."""
    from google.genai import types as genai_types

    client = _get_gemini_client()
    models_to_try = candidate_models or [
        settings.GEMINI_MODEL,
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-flash-latest",
    ]
    deduped_models: list[str] = []
    seen: set[str] = set()
    for m in models_to_try:
        if m not in seen:
            seen.add(m)
            deduped_models.append(m)

    last_error: Exception | None = None
    for model_name in deduped_models:
        logger.debug("sending_prompt_to_gemini_llm", model=model_name)
        for attempt in range(2):
            try:

                def _generate(
                    current_client: Any, target_model: str = model_name
                ) -> str:
                    response = current_client.models.generate_content(
                        model=target_model,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=0.2,
                            top_p=1.0,
                            max_output_tokens=1024,
                        ),
                    )
                    return response.text or ""

                text = await asyncio.to_thread(_generate, client, model_name)
                if text and text.strip():
                    return text.strip()
                raise DocumentProcessingError(
                    f"Gemini model '{model_name}' returned an empty response."
                )

            except Exception as e:
                last_error = e
                err_str = str(e)
                is_transient = any(
                    token in err_str
                    for token in (
                        "429",
                        "500",
                        "502",
                        "503",
                        "504",
                        "RESOURCE_EXHAUSTED",
                        "UNAVAILABLE",
                        "demand",
                    )
                )
                if is_transient and attempt == 0:
                    logger.warning(
                        "gemini_llm_transient_error_retrying",
                        model=model_name,
                        attempt=1,
                        error=err_str,
                    )
                    await asyncio.sleep(1.5)
                    continue
                logger.warning(
                    "gemini_model_attempt_failed", model=model_name, error=err_str
                )
                break  # Try next candidate model

    if last_error:
        raise DocumentProcessingError(
            f"All Gemini models failed. Last error: {str(last_error)}"
        ) from last_error
    raise DocumentProcessingError("Failed to generate response from Gemini API")


async def generate_response_from_llm(prompt: str) -> str:
    """Generate response with failover between Gemini and Groq/OpenAI."""
    primary_provider = (settings.LLM_PROVIDER or "gemini").lower()

    if primary_provider == "gemini":
        try:
            return await _generate_with_gemini(prompt)
        except Exception as gemini_err:
            logger.warning(
                "gemini_primary_llm_failed_attempting_failover",
                error=str(gemini_err),
            )
            has_groq = bool(
                settings.GROQ_API_KEY or settings.LLM_API_KEY or settings.OPENAI_API_KEY
            )
            if has_groq:
                try:
                    logger.info("failing_over_to_groq_llm")
                    return await _generate_with_openai_compatible(
                        prompt, provider_override="groq"
                    )
                except Exception as groq_err:
                    logger.error(
                        "all_llm_providers_failed",
                        gemini_error=str(gemini_err),
                        groq_error=str(groq_err),
                    )
                    err_summary = f"{gemini_err} | {groq_err}"
                    raise DocumentProcessingError(
                        f"Both Gemini and Groq failover failed: {err_summary}"
                    ) from groq_err
            raise gemini_err
    else:
        try:
            return await _generate_with_openai_compatible(prompt)
        except Exception as openai_err:
            logger.warning(
                "openai_compatible_primary_llm_failed_attempting_failover",
                provider=primary_provider,
                error=str(openai_err),
            )
            if settings.GEMINI_API_KEY:
                try:
                    logger.info("failing_over_to_gemini_llm")
                    return await _generate_with_gemini(prompt)
                except Exception as gemini_err:
                    logger.error(
                        "all_llm_providers_failed",
                        openai_error=str(openai_err),
                        gemini_error=str(gemini_err),
                    )
                    err_summary = f"{openai_err} | {gemini_err}"
                    raise DocumentProcessingError(
                        f"Both {primary_provider} and Gemini failed: {err_summary}"
                    ) from gemini_err
            raise openai_err


async def _stream_with_gemini(
    prompt: str, candidate_models: list[str] | None = None
) -> AsyncIterator[str]:
    """Stream response tokens using Gemini API with candidate model failover."""
    from google.genai import types as genai_types

    client = _get_gemini_client()
    models_to_try = candidate_models or [
        settings.GEMINI_MODEL,
        "gemini-3.8-flash",
    ]
    deduped_models: list[str] = []
    seen: set[str] = set()
    for m in models_to_try:
        if m not in seen:
            seen.add(m)
            deduped_models.append(m)

    last_error: Exception | None = None
    for model_name in deduped_models:
        logger.debug("streaming_prompt_to_gemini_llm", model=model_name)
        try:
            stream = await client.aio.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.2,
                    top_p=1.0,
                    max_output_tokens=1024,
                ),
            )
            yielded = False
            async for chunk in stream:
                text = chunk.text or ""
                if text:
                    yielded = True
                    yield text
            if yielded:
                return
        except Exception as e:
            last_error = e
            logger.warning(
                "gemini_stream_failed_trying_next_model",
                model=model_name,
                error=str(e),
            )
            continue

    if last_error:
        raise DocumentProcessingError(
            f"All Gemini models failed to stream: {str(last_error)}"
        ) from last_error
    raise DocumentProcessingError("Failed to stream response from Gemini API")


async def _stream_with_openai_compatible(
    prompt: str, provider_override: str | None = None
) -> AsyncIterator[str]:
    """Stream response tokens using an OpenAI-compatible endpoint."""
    api_key, model, base_url = _resolve_openai_compatible_config(provider_override)
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    active_provider = provider_override or settings.LLM_PROVIDER
    logger.debug(
        "streaming_prompt_to_openai_compatible_llm",
        provider=active_provider,
        model=model,
    )

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
        stream=True,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta.content if chunk.choices else ""
        if delta:
            yield delta


async def generate_stream_from_llm(prompt: str) -> AsyncIterator[str]:
    """Stream response tokens with failover between Gemini and Groq/OpenAI."""
    primary_provider = (settings.LLM_PROVIDER or "gemini").lower()

    if primary_provider == "gemini":
        try:
            async for token in _stream_with_gemini(prompt):
                yield token
            return
        except Exception as gemini_err:
            logger.warning(
                "gemini_primary_stream_failed_attempting_failover",
                error=str(gemini_err),
            )
            has_groq = bool(
                settings.GROQ_API_KEY or settings.LLM_API_KEY or settings.OPENAI_API_KEY
            )
            if has_groq:
                logger.info("failing_over_to_groq_streaming")
                async for token in _stream_with_openai_compatible(
                    prompt, provider_override="groq"
                ):
                    yield token
                return
            raise gemini_err
    else:
        try:
            async for token in _stream_with_openai_compatible(prompt):
                yield token
            return
        except Exception as openai_err:
            logger.warning(
                "openai_compatible_stream_failed_attempting_failover",
                provider=primary_provider,
                error=str(openai_err),
            )
            if settings.GEMINI_API_KEY:
                logger.info("failing_over_to_gemini_streaming")
                async for token in _stream_with_gemini(prompt):
                    yield token
                return
            raise openai_err

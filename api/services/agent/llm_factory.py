from typing import Any

from pydantic import SecretStr

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)


def _get_gemini_model() -> Any | None:
    if not settings.GEMINI_API_KEY:
        return None
    from langchain_google_genai import ChatGoogleGenerativeAI

    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash-lite"
    if model_name == "gemini-2.5-flash":
        model_name = "gemini-2.5-flash-lite"
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
        max_retries=1,
    )


def _get_groq_model() -> Any | None:
    groq_key = settings.GROQ_API_KEY or settings.LLM_API_KEY
    if not groq_key:
        return None
    from langchain_openai import ChatOpenAI

    groq_model_name = settings.LLM_MODEL or "openai/gpt-oss-120b"
    if not groq_model_name or "gemini" in groq_model_name.lower():
        groq_model_name = "openai/gpt-oss-120b"
    return ChatOpenAI(
        model=groq_model_name,
        api_key=SecretStr(groq_key),
        base_url="https://api.groq.com/openai/v1",
        temperature=0.2,
        max_retries=2,
    )


def _get_openai_model() -> Any:
    from langchain_openai import ChatOpenAI

    api_key = settings.OPENAI_API_KEY or settings.LLM_API_KEY
    if not api_key:
        raise DocumentProcessingError("OPENAI_API_KEY is not configured.")
    model = settings.OPENAI_MODEL or "gpt-4o-mini"
    logger.info("agent_llm_configured", primary="openai", fallback=None)
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        temperature=0.2,
    )


def get_agent_chat_model() -> Any:
    """Return configured LangChain chat model with resilient dual-provider fallback."""
    provider = (settings.LLM_PROVIDER or "groq").lower()

    gemini_model = _get_gemini_model()
    groq_model = _get_groq_model()

    if groq_model is not None and gemini_model is not None:
        if provider == "gemini":
            logger.info("agent_llm_configured", primary="gemini", fallback="groq")
            return gemini_model.with_fallbacks([groq_model])
        logger.info("agent_llm_configured", primary="groq", fallback="gemini")
        return groq_model.with_fallbacks([gemini_model])

    if groq_model is not None:
        logger.info("agent_llm_configured", primary="groq", fallback=None)
        return groq_model
    if gemini_model is not None:
        logger.info("agent_llm_configured", primary="gemini", fallback=None)
        return gemini_model
    if provider == "openai":
        return _get_openai_model()

    raise DocumentProcessingError(
        f"Unsupported LLM provider '{provider}'. Set GROQ_API_KEY or GEMINI_API_KEY."
    )

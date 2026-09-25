from typing import Any

from pydantic import SecretStr

from api.core.config import settings
from api.core.exceptions import DocumentProcessingError
from api.core.logging import get_logger

logger = get_logger(__name__)


def get_agent_chat_model() -> Any:
    """Return configured LangChain chat model based on application settings."""
    provider = (settings.LLM_PROVIDER or "gemini").lower()

    if provider == "gemini" or (not provider and settings.GEMINI_API_KEY):
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.GEMINI_API_KEY:
            raise DocumentProcessingError("GEMINI_API_KEY is not configured.")
        model = settings.GEMINI_MODEL or "gemini-2.5-flash"
        logger.debug("initialized_gemini_chat_model", model=model)
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2,
        )

    if provider == "groq" or settings.GROQ_API_KEY:
        from langchain_openai import ChatOpenAI

        api_key = settings.GROQ_API_KEY or settings.LLM_API_KEY
        if not api_key:
            raise DocumentProcessingError("GROQ_API_KEY is not configured.")
        model = settings.LLM_MODEL or "qwen/qwen3.8-27b"
        logger.debug("initialized_groq_chat_model", model=model)
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url="https://api.groq.com/openai/v1",
            temperature=0.2,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = settings.OPENAI_API_KEY or settings.LLM_API_KEY
        if not api_key:
            raise DocumentProcessingError("OPENAI_API_KEY is not configured.")
        model = settings.OPENAI_MODEL or "gpt-4o-mini"
        logger.debug("initialized_openai_chat_model", model=model)
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            temperature=0.2,
        )

    raise DocumentProcessingError(
        f"Unsupported LLM provider '{provider}'. Set GEMINI_API_KEY or GROQ_API_KEY."
    )

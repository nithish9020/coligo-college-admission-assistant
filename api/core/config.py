from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Coligo College Admission Assistant API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Docs / Swagger Settings
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://dte:dte_secret@localhost:5432/dte_chatbot"

    # LLM Provider & Model Selection
    # Supported: "gemini" | "groq" | "openai" | "deepseek" | "ollama" | "custom"
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "openai/gpt-oss-20b"
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str | None = None
    GROQ_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None

    # Google Gemini API Settings
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768

    # OpenAI / Compatible API Settings — used for brochure extraction
    # and alternative LLM backend (Groq, DeepSeek, Ollama)
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # RAG Settings
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 6

    # Conversation memory. TTL matches WhatsApp's own 24h service-conversation
    # window: a student returning the next day starts a fresh thread.
    # MAX_TURNS caps how much history reaches the prompt (12 = ~6 exchanges).
    CONVERSATION_TTL_HOURS: int = 24
    CONVERSATION_MAX_TURNS: int = 12
    # Condense follow-ups into standalone questions before embedding. Costs one
    # extra LLM call per message that has history; disable to save Gemini quota
    # at the cost of follow-up questions retrieving the wrong chunks.
    ENABLE_QUERY_REWRITING: bool = True
    USE_LANGGRAPH: bool = True

    # Redis & Asynchronous Caching Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    CUTOFF_CACHE_TTL_SECONDS: int = 86400  # 24 hours

    # Speech & Voice Note Settings (Edge-TTS)
    ENABLE_VOICE_RESPONSES: bool = True
    DEFAULT_TAMIL_VOICE: str = "ta-IN-PallaviNeural"
    DEFAULT_ENGLISH_VOICE: str = "en-IN-NeerjaNeural"

    # Hybrid Search & Reranking Settings
    ENABLE_HYBRID_SEARCH: bool = True
    ENABLE_RERANKING: bool = True
    RERANKER_MODEL: str = "ms-marco-TinyBERT-L-2-v2"

    # WhatsApp Cloud API (Meta) — see README "WhatsApp Integration"
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_API_VERSION: str = "v21.0"
    ADMIN_NUMBERS: str = ""

    # Administration Portal — Auth Settings
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    # 7 days, to support "remember me" login persistence
    JWT_EXPIRE_MINUTES: int = 10080

    # Administration Portal — Fixed Platform Admin Login
    ADMIN_EMAIL: str = "admin@coligo.com"
    ADMIN_PASSWORD: str = "coligo@123"

    # Administration Portal — File Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_LOGO_SIZE_MB: int = 2
    MAX_BROCHURE_SIZE_MB: int = 10

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def admin_numbers_list(self) -> list[str]:
        return [n.strip() for n in self.ADMIN_NUMBERS.split(",") if n.strip()]


settings = Settings()

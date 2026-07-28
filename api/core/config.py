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

    # Gemini API Settings
    GEMINI_API_KEY: str | None = None
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-005"

    # RAG Settings
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

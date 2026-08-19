from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.core import settings
from api.core.exceptions import (
    BrochureExtractionError,
    CorruptedDocumentError,
    DocumentNotFoundError,
    DuplicateEmailError,
    EmptyDocumentTextError,
    InvalidCredentialsError,
    InvalidDocumentRefError,
    InvalidFileError,
    NotAuthenticatedError,
    NotAuthorizedError,
    ResourceNotFoundError,
)
from api.core.logging import configure_logging, get_logger
from api.core.middleware import RequestLoggingMiddleware
from api.routers import (
    analytics_router,
    auth_router,
    brochure_router,
    chat_router,
    college_router,
    course_router,
    document_router,
    escalation_router,
    facility_router,
    health_router,
    whatsapp_router,
)

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "app_started", environment=settings.ENVIRONMENT, docs_url=settings.DOCS_URL
    )
    from sqlalchemy import text

    import api.models  # noqa: F401
    from api.core.database import Base, engine

    logger.info("initializing_database_tables_at_startup")
    try:
        async with engine.begin() as conn:
            # Create vector extension if not present
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            # Create all mapped tables safely (if not already existing)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_initialized_successfully")
    except Exception as e:
        logger.error("database_table_initialization_failed", error=str(e))

    yield
    logger.info("app_stopped")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
### Coligo College Admission Assistant API
Modern, scalable backend service providing API endpoints for college admission
counseling, RAG document search, and user interactions.

#### Key Features:
* 🩺 **Health Checks**: Endpoint `/health` and `/health/detailed` for monitoring.
* 💬 **WhatsApp Webhook**: `/webhook` receives and routes Meta Cloud API events.
* 📚 **Interactive Swagger Documentation**: Available at `/docs`.
* 📖 **ReDoc Documentation**: Available at `/redoc`.
""",
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    swagger_ui_parameters={"docExpansion": "list", "deepLinking": True},
    lifespan=lifespan,
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging (equivalent of pino-http) — added last so it wraps
# everything else and captures true end-to-end request duration.
app.add_middleware(RequestLoggingMiddleware)

# Include Routers
app.include_router(health_router)
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(whatsapp_router)
app.include_router(auth_router)
app.include_router(college_router)
app.include_router(course_router)
app.include_router(facility_router)
app.include_router(brochure_router)
app.include_router(escalation_router)
app.include_router(analytics_router)


# Register global exception handlers for document processing errors
@app.exception_handler(InvalidDocumentRefError)
async def invalid_document_ref_handler(
    request: Request, exc: InvalidDocumentRefError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(DocumentNotFoundError)
async def document_not_found_handler(
    request: Request, exc: DocumentNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(CorruptedDocumentError)
async def corrupted_document_handler(
    request: Request, exc: CorruptedDocumentError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(EmptyDocumentTextError)
async def empty_document_text_handler(
    request: Request, exc: EmptyDocumentTextError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(BrochureExtractionError)
async def brochure_extraction_error_handler(
    request: Request, exc: BrochureExtractionError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(exc)},
    )


# Register global exception handlers for administration portal (auth/college) errors
@app.exception_handler(DuplicateEmailError)
async def duplicate_email_handler(
    request: Request, exc: DuplicateEmailError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)}
    )


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(
    request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)}
    )


@app.exception_handler(NotAuthenticatedError)
async def not_authenticated_handler(
    request: Request, exc: NotAuthenticatedError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)}
    )


@app.exception_handler(NotAuthorizedError)
async def not_authorized_handler(
    request: Request, exc: NotAuthorizedError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)}
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(
    request: Request, exc: ResourceNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
    )


@app.exception_handler(InvalidFileError)
async def invalid_file_handler(request: Request, exc: InvalidFileError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)}
    )


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Welcome to Coligo API",
        "docs": settings.DOCS_URL,
        "health": "/health",
    }

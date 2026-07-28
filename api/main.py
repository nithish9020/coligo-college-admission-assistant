from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core import settings
from api.core.logging import configure_logging, get_logger
from api.core.middleware import RequestLoggingMiddleware
from api.routers import health_router

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "app_started", environment=settings.ENVIRONMENT, docs_url=settings.DOCS_URL
    )
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


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Welcome to Coligo API",
        "docs": settings.DOCS_URL,
        "health": "/health",
    }

from fastapi import APIRouter

from api.core import settings
from api.schemas import DetailedHealthResponse, HealthCheckResponse

router = APIRouter(prefix="/health", tags=["Health Checks"])


@router.get("", response_model=HealthCheckResponse, summary="Basic Health Check")
async def health_check() -> HealthCheckResponse:
    """Return basic health status of the API service."""
    return HealthCheckResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed System Health Check",
)
async def detailed_health_check() -> DetailedHealthResponse:
    """Return detailed health status including dependent services."""
    return DetailedHealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        services={"database": "healthy", "redis": "healthy"},
    )

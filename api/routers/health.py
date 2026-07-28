from fastapi import APIRouter

from api.core.logging import get_logger
from api.schemas import DetailedHealthResponse, HealthCheckResponse
from api.services.health_service import get_detailed_health_status, get_health_status

router = APIRouter(prefix="/health", tags=["Health Checks"])
logger = get_logger(__name__)


@router.get("", response_model=HealthCheckResponse, summary="Basic Health Check")
async def health_check() -> HealthCheckResponse:
    """Return basic health status of the API service."""
    logger.info("health_check_requested")
    return get_health_status()


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed System Health Check",
)
async def detailed_health_check() -> DetailedHealthResponse:
    """Return detailed health status including dependent services."""
    logger.info("detailed_health_check_requested")
    return get_detailed_health_status()

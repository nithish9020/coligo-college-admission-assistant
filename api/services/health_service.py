from api.core.config import settings
from api.core.logging import get_logger
from api.schemas import DetailedHealthResponse, HealthCheckResponse

logger = get_logger(__name__)


def get_health_status() -> HealthCheckResponse:
    logger.debug("health_status_computed")
    return HealthCheckResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )


def get_detailed_health_status() -> DetailedHealthResponse:
    services = {"database": "healthy", "redis": "healthy"}
    logger.debug("detailed_health_status_computed", dependencies=services)
    return DetailedHealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        services=services,
    )

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(..., examples=["healthy"])
    environment: str = Field(..., examples=["development"])
    version: str = Field(..., examples=["0.1.0"])


class DetailedHealthResponse(HealthCheckResponse):
    services: dict[str, str] = Field(
        default_factory=lambda: {"database": "healthy", "redis": "healthy"}
    )

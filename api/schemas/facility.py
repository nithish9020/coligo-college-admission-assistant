from datetime import datetime

from pydantic import BaseModel, Field


class FacilityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class FacilityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class FacilityResponse(BaseModel):
    id: int
    college_id: int
    name: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

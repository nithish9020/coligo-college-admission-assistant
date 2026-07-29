from datetime import datetime

from pydantic import BaseModel, Field, field_validator

VALID_PROGRAM_LEVELS = {"UG", "PG", "Diploma", "PhD"}
VALID_STATUSES = {"published", "draft"}


class CourseCreate(BaseModel):
    program_level: str = Field(..., examples=["UG"])
    course_name: str = Field(..., min_length=2, max_length=255)
    course_code: str | None = None
    duration: str | None = None
    intake_capacity: int | None = Field(None, ge=0)
    department: str | None = None
    status: str = "draft"

    eligibility: str | None = None
    fees: str | None = None
    course_details: str | None = None
    career_opportunities: str | None = None

    @field_validator("program_level")
    @classmethod
    def validate_program_level(cls, v: str) -> str:
        if v not in VALID_PROGRAM_LEVELS:
            raise ValueError(
                f"program_level must be one of {sorted(VALID_PROGRAM_LEVELS)}"
            )
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


class CourseUpdate(BaseModel):
    program_level: str | None = None
    course_name: str | None = Field(None, min_length=2, max_length=255)
    course_code: str | None = None
    duration: str | None = None
    intake_capacity: int | None = Field(None, ge=0)
    department: str | None = None
    status: str | None = None

    eligibility: str | None = None
    fees: str | None = None
    course_details: str | None = None
    career_opportunities: str | None = None

    @field_validator("program_level")
    @classmethod
    def validate_program_level(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_PROGRAM_LEVELS:
            raise ValueError(
                f"program_level must be one of {sorted(VALID_PROGRAM_LEVELS)}"
            )
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


class CourseResponse(BaseModel):
    id: int
    college_id: int
    program_level: str
    course_name: str
    course_code: str | None = None
    duration: str | None = None
    intake_capacity: int | None = None
    department: str | None = None
    status: str

    eligibility: str | None = None
    fees: str | None = None
    course_details: str | None = None
    career_opportunities: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime

from pydantic import BaseModel, Field


class CollegeProfileUpdate(BaseModel):
    """All fields optional so the profile can be updated section by section."""

    college_name: str | None = Field(None, min_length=2, max_length=255)
    college_type: str | None = None
    established_year: int | None = Field(None, ge=1800, le=2100)
    affiliated_university: str | None = None
    about: str | None = Field(None, max_length=2000)

    contact_person: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None

    website: str | None = None
    facebook: str | None = None
    twitter: str | None = None
    linkedin: str | None = None
    instagram: str | None = None

    accreditation: str | None = None


class CollegeProfileResponse(BaseModel):
    id: int
    email: str
    is_active: bool

    college_name: str
    college_type: str | None = None
    established_year: int | None = None
    affiliated_university: str | None = None
    logo_path: str | None = None
    about: str | None = None

    contact_person: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None

    website: str | None = None
    facebook: str | None = None
    twitter: str | None = None
    linkedin: str | None = None
    instagram: str | None = None

    accreditation: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollegeListItem(BaseModel):
    id: int
    college_name: str
    email: str
    contact_person: str | None = None
    is_active: bool
    course_count: int = 0
    brochure_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CollegeDetailResponse(CollegeProfileResponse):
    course_count: int = 0
    brochure_count: int = 0
    facility_count: int = 0

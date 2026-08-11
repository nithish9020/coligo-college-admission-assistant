from pydantic import BaseModel

from api.schemas.college import CollegeProfileUpdate
from api.schemas.course import CourseCreate
from api.schemas.facility import FacilityCreate


class ExtractedCollegeProfile(BaseModel):
    """Loosely-typed suggestion — not applied to the DB until reviewed and
    resubmitted through CollegeProfileUpdate, which does the real validation."""

    college_type: str | None = None
    established_year: int | None = None
    affiliated_university: str | None = None
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


class ExtractedCourse(BaseModel):
    program_level: str | None = None
    course_name: str
    course_code: str | None = None
    duration: str | None = None
    intake_capacity: int | None = None
    department: str | None = None
    eligibility: str | None = None
    fees: str | None = None
    course_details: str | None = None
    career_opportunities: str | None = None


class ExtractedFacility(BaseModel):
    name: str
    description: str | None = None


class BrochureExtractionResult(BaseModel):
    """Suggested details parsed from a brochure PDF, for the college to review
    and edit before anything is written to the database."""

    college_profile: ExtractedCollegeProfile
    courses: list[ExtractedCourse] = []
    facilities: list[ExtractedFacility] = []


class ApplyBrochureExtractionRequest(BaseModel):
    """The reviewed/edited subset of a BrochureExtractionResult the college
    confirmed should actually be written. Reuses the same schemas as manual
    entry so this gets the same validation as the ordinary profile/course/
    facility forms."""

    college_profile: CollegeProfileUpdate | None = None
    courses: list[CourseCreate] = []
    facilities: list[FacilityCreate] = []

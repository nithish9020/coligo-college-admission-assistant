from api.schemas.auth import (
    CollegeSignupRequest,
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from api.schemas.brochure import BrochureResponse, BrochureUpdate
from api.schemas.brochure_extraction import (
    ApplyBrochureExtractionRequest,
    BrochureExtractionResult,
    ExtractedCollegeProfile,
    ExtractedCourse,
    ExtractedFacility,
)
from api.schemas.chat import ChatRequest, ChatResponse
from api.schemas.college import (
    CollegeDetailResponse,
    CollegeListItem,
    CollegeProfileResponse,
    CollegeProfileUpdate,
)
from api.schemas.course import CourseCreate, CourseResponse, CourseUpdate
from api.schemas.document import DocumentProcessRequest, DocumentProcessResponse
from api.schemas.facility import FacilityCreate, FacilityResponse, FacilityUpdate
from api.schemas.health import DetailedHealthResponse, HealthCheckResponse
from api.schemas.whatsapp import ParsedMessage, WhatsAppWebhookPayload

__all__ = [
    "HealthCheckResponse",
    "DetailedHealthResponse",
    "DocumentProcessRequest",
    "DocumentProcessResponse",
    "ChatRequest",
    "ChatResponse",
    "WhatsAppWebhookPayload",
    "ParsedMessage",
    "CollegeSignupRequest",
    "LoginRequest",
    "TokenResponse",
    "CurrentUserResponse",
    "CollegeProfileUpdate",
    "CollegeProfileResponse",
    "CollegeListItem",
    "CollegeDetailResponse",
    "CourseCreate",
    "CourseUpdate",
    "CourseResponse",
    "FacilityCreate",
    "FacilityUpdate",
    "FacilityResponse",
    "BrochureUpdate",
    "BrochureResponse",
    "ExtractedCollegeProfile",
    "ExtractedCourse",
    "ExtractedFacility",
    "BrochureExtractionResult",
    "ApplyBrochureExtractionRequest",
]

from api.routers.analytics import router as analytics_router
from api.routers.auth import router as auth_router
from api.routers.brochure import router as brochure_router
from api.routers.chat import router as chat_router
from api.routers.college import router as college_router
from api.routers.course import router as course_router
from api.routers.cutoff import router as cutoff_router
from api.routers.document import router as document_router
from api.routers.escalation import router as escalation_router
from api.routers.facility import router as facility_router
from api.routers.health import router as health_router
from api.routers.whatsapp import router as whatsapp_router

__all__ = [
    "health_router",
    "document_router",
    "chat_router",
    "whatsapp_router",
    "auth_router",
    "college_router",
    "course_router",
    "facility_router",
    "brochure_router",
    "escalation_router",
    "analytics_router",
    "cutoff_router",
]

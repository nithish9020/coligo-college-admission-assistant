from api.routers.chat import router as chat_router
from api.routers.document import router as document_router
from api.routers.health import router as health_router
from api.routers.whatsapp import router as whatsapp_router

__all__ = ["health_router", "document_router", "chat_router", "whatsapp_router"]

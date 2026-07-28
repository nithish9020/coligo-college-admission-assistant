import hashlib
import hmac

from api.core.config import settings
from api.core.logging import get_logger
from api.schemas.whatsapp import ParsedMessage, WhatsAppWebhookPayload

logger = get_logger(__name__)

# Admin commands documented in README's "WhatsApp Integration" table.
# Detection only in this pass — none of these actually execute yet.
ADMIN_COMMANDS = ("/ingest", "/stats", "/refresh", "/health")


def verify_signature(
    raw_body: bytes, signature_header: str | None, app_secret: str
) -> bool:
    """Verify Meta's `X-Hub-Signature-256` header over the raw request body."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


def extract_message(payload: WhatsAppWebhookPayload) -> ParsedMessage | None:
    """Pull the first user message out of a webhook payload.

    Returns None for status-only callbacks (delivered/read receipts), which
    Meta sends constantly and which aren't user messages to route.
    """
    for entry in payload.entry:
        for change in entry.changes:
            messages = change.value.messages
            if not messages:
                continue
            message = messages[0]
            logger.debug(
                "message_extracted", sender=message.from_number, type=message.type
            )
            return ParsedMessage(
                sender=message.from_number,
                message_type=message.type,
                text=message.text.body if message.text else None,
                message_id=message.id,
            )
    logger.debug("no_message_in_payload")
    return None


def is_admin_number(sender: str) -> bool:
    return sender in settings.admin_numbers_list


def match_admin_command(text: str | None) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    for command in ADMIN_COMMANDS:
        if stripped == command or stripped.startswith(f"{command} "):
            return command
    return None

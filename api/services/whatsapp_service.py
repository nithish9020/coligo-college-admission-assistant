import hashlib
import hmac

import httpx

from api.core.config import settings
from api.core.logging import get_logger
from api.schemas.whatsapp import ParsedMessage, WhatsAppWebhookPayload

logger = get_logger(__name__)

# Admin commands documented in README's "WhatsApp Integration" table.
# Detection only — none of these execute yet (need ingest/analytics services).
ADMIN_COMMANDS = ("/ingest", "/stats", "/refresh", "/health")

# Meta rejects text bodies over 4096 characters.
MAX_MESSAGE_LENGTH = 4096


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


async def send_text(to: str, body: str) -> bool:
    """Send a text message back to a user via the WhatsApp Cloud API.

    Returns True on success. Failures are logged and swallowed rather than
    raised — a failed reply must never stop the webhook from acking Meta
    with 200, otherwise Meta retries and the user gets duplicate replies.
    """
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("send_text_skipped_missing_credentials", to=to)
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:MAX_MESSAGE_LENGTH]},
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, json=payload, headers=headers, timeout=15.0
            )
        if response.status_code >= 400:
            logger.error(
                "send_text_failed",
                to=to,
                status_code=response.status_code,
                body=response.text,
            )
            return False
        logger.info("send_text_succeeded", to=to)
        return True
    except httpx.RequestError as e:
        logger.error("send_text_request_error", to=to, error=str(e))
        return False

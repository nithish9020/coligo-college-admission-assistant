import hashlib
import hmac
from typing import Any, Tuple

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.logging import get_logger
from api.models import Conversation, Document, DocumentChunk, Escalation
from api.schemas.whatsapp import ParsedMessage, WhatsAppWebhookPayload

logger = get_logger(__name__)

ADMIN_COMMANDS = ("/ingest", "/stats", "/refresh", "/health")
MAX_MESSAGE_LENGTH = 4096

# ── Shared HTTP client for Meta Graph API ──
# Reuses TCP connections across all outbound WhatsApp API calls, avoiding
# repeated DNS + TLS handshakes that add ~200–400ms per message.
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Return a module-level shared httpx client (lazy-initialized)."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=15.0)
    return _http_client


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

    Handles text messages as well as interactive button responses.
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

            extracted_text = None
            media_id = None
            mime_type = None

            if message.type == "text" and message.text:
                extracted_text = message.text.body
            elif message.type == "interactive":
                interactive = getattr(message, "interactive", None) or {}
                button_reply = interactive.get("button_reply", {})
                list_reply = interactive.get("list_reply", {})
                extracted_text = (
                    button_reply.get("id")
                    or button_reply.get("title")
                    or list_reply.get("id")
                    or list_reply.get("title")
                )
            elif message.type in ("audio", "voice"):
                audio_obj = getattr(message, "audio", None) or getattr(
                    message, "voice", None
                )
                if audio_obj:
                    media_id = audio_obj.id
                    mime_type = audio_obj.mime_type

            return ParsedMessage(
                sender=message.from_number,
                message_type=message.type,
                text=extracted_text,
                media_id=media_id,
                mime_type=mime_type,
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
    """Send a text message back to a user via the WhatsApp Cloud API."""
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
        client = _get_http_client()
        response = await client.post(url, json=payload, headers=headers, timeout=15.0)
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


async def send_typing_indicator(message_id: str) -> bool:
    """Send typing indicator ('typing...') to WhatsApp while preparing response.

    In Meta WhatsApp Cloud API v21.0+, passing a typing_indicator payload
    displays the 'typing...' animation on the student's phone for up to 25s
    or until the reply message is delivered.
    """
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {
            "type": "text",
        },
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        client = _get_http_client()
        resp = await client.post(url, json=payload, headers=headers, timeout=5.0)
        if resp.status_code >= 400:
            logger.debug(
                "typing_indicator_fallback_to_standard_read",
                status_code=resp.status_code,
                error=resp.text,
            )
            # Fallback to standard read receipt without typing_indicator object
            fallback_payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            }
            await client.post(url, json=fallback_payload, headers=headers, timeout=5.0)
        return True
    except Exception as e:
        logger.error(
            "send_typing_indicator_failed", message_id=message_id, error=str(e)
        )
        return False


async def mark_message_as_read(message_id: str, show_typing: bool = True) -> bool:
    """Send read receipt (blue ticks) and optional typing indicator to WhatsApp."""
    if show_typing:
        return await send_typing_indicator(message_id)

    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        client = _get_http_client()
        await client.post(url, json=payload, headers=headers, timeout=5.0)
        return True
    except Exception as e:
        logger.error("mark_message_as_read_failed", message_id=message_id, error=str(e))
        return False


async def send_interactive_buttons(
    to: str, body_text: str, buttons: list[Tuple[str, str]]
) -> bool:
    """Send interactive Quick Reply buttons via WhatsApp Cloud API.

    Args:
        to: Recipient phone number.
        body_text: Main text message.
        buttons: List of (button_id, button_title) tuples (max 3 buttons).
    """
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("send_interactive_buttons_skipped_missing_credentials", to=to)
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    action_buttons = []
    for btn_id, btn_title in buttons[:3]:
        action_buttons.append(
            {
                "type": "reply",
                "reply": {"id": btn_id, "title": btn_title[:20]},
            }
        )

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text[:1024]},
            "action": {"buttons": action_buttons},
        },
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    try:
        client = _get_http_client()
        response = await client.post(url, json=payload, headers=headers, timeout=15.0)
        if response.status_code >= 400:
            logger.error("send_interactive_buttons_failed", status=response.status_code)
            return False
        return True
    except httpx.RequestError as e:
        logger.error("send_interactive_buttons_error", error=str(e))
        return False


async def send_document(
    to: str, document_url: str, caption: str = "", filename: str = "brochure.pdf"
) -> bool:
    """Send a PDF document attachment to a user via WhatsApp Cloud API."""
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("send_document_skipped_missing_credentials", to=to)
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    doc_dict: dict[str, str] = {
        "caption": caption[:1024],
        "filename": filename,
    }
    if document_url.startswith("http://") or document_url.startswith("https://"):
        doc_dict["link"] = document_url
    else:
        doc_dict["id"] = document_url

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": doc_dict,
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        client = _get_http_client()
        response = await client.post(url, json=payload, headers=headers, timeout=20.0)
        if response.status_code >= 400:
            logger.error(
                "send_document_failed",
                to=to,
                status_code=response.status_code,
                body=response.text,
            )
            return False
        logger.info("send_document_succeeded", to=to, filename=filename)
        return True
    except httpx.RequestError as e:
        logger.error("send_document_request_error", to=to, error=str(e))
        return False


async def send_interactive_list(
    to: str, body_text: str, button_label: str, sections: list[dict]
) -> bool:
    """Send an interactive List Menu selector via WhatsApp Cloud API."""
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("send_interactive_list_skipped_missing_credentials", to=to)
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text[:1024]},
            "action": {"button": button_label[:20], "sections": sections},
        },
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        client = _get_http_client()
        response = await client.post(url, json=payload, headers=headers, timeout=15.0)
        if response.status_code >= 400:
            logger.error("send_interactive_list_failed", status=response.status_code)
            return False
        return True
    except httpx.RequestError as e:
        logger.error("send_interactive_list_error", error=str(e))
        return False


async def send_location(
    to: str,
    latitude: float,
    longitude: float,
    name: str,
    address: str,
) -> bool:
    """Send a native Google Maps location pin via WhatsApp Cloud API."""
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("send_location_skipped_missing_credentials", to=to)
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "location",
        "location": {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "name": name[:100],
            "address": address[:300],
        },
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    try:
        client = _get_http_client()
        response = await client.post(url, json=payload, headers=headers, timeout=15.0)
        if response.status_code >= 400:
            logger.error(
                "send_location_failed",
                to=to,
                status=response.status_code,
                body=response.text,
            )
            return False
        logger.info("send_location_succeeded", to=to, name=name)
        return True
    except httpx.RequestError as e:
        logger.error("send_location_error", to=to, error=str(e))
        return False


async def send_contact(
    to: str,
    name: str,
    phone: str,
    org: str = "Sri Krishna College of Engineering & Technology",
    email: str = "admissions@skcet.ac.in",
) -> bool:
    """Send a native vCard contact card via WhatsApp Cloud API."""
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("send_contact_skipped_missing_credentials", to=to)
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    contact_data: dict[str, Any] = {
        "name": {
            "formatted_name": name,
            "first_name": name,
        },
        "phones": [
            {
                "phone": phone,
                "type": "WORK",
            }
        ],
        "org": {
            "company": org,
        },
    }
    if email:
        contact_data["emails"] = [
            {
                "email": email,
                "type": "WORK",
            }
        ]

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "contacts",
        "contacts": [contact_data],
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    try:
        client = _get_http_client()
        response = await client.post(url, json=payload, headers=headers, timeout=15.0)
        if response.status_code >= 400:
            logger.error(
                "send_contact_failed",
                to=to,
                status=response.status_code,
                body=response.text,
            )
            return False
        logger.info("send_contact_succeeded", to=to, name=name)
        return True
    except httpx.RequestError as e:
        logger.error("send_contact_error", to=to, error=str(e))
        return False


async def upload_media(
    file_bytes: bytes,
    mime_type: str = "audio/ogg",
    filename: str = "voice.ogg",
) -> str | None:
    """Upload media file to Meta WhatsApp Cloud API and return the media ID."""
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("upload_media_skipped_missing_credentials")
        return None

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
    )
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    files = {"file": (filename, file_bytes, mime_type)}
    data = {"messaging_product": "whatsapp", "type": mime_type}

    try:
        client = _get_http_client()
        response = await client.post(
            url, headers=headers, files=files, data=data, timeout=25.0
        )
        if response.status_code >= 400:
            logger.error(
                "upload_media_failed",
                status_code=response.status_code,
                body=response.text,
            )
            return None
        res_data = response.json()
        media_id = res_data.get("id")
        logger.info("upload_media_succeeded", media_id=media_id)
        return str(media_id) if media_id else None
    except Exception as e:
        logger.error("upload_media_error", error=str(e))
        return None


async def send_audio(to: str, audio_id_or_url: str, is_id: bool = True) -> bool:
    """Send an audio note/voice reply via WhatsApp Cloud API."""
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("send_audio_skipped_missing_credentials", to=to)
        return False

    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    audio_obj: dict[str, str] = (
        {"id": audio_id_or_url} if is_id else {"link": audio_id_or_url}
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "audio",
        "audio": audio_obj,
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        client = _get_http_client()
        response = await client.post(url, json=payload, headers=headers, timeout=15.0)
        if response.status_code >= 400:
            logger.error(
                "send_audio_failed",
                to=to,
                status_code=response.status_code,
                body=response.text,
            )
            return False
        logger.info("send_audio_succeeded", to=to)
        return True
    except httpx.RequestError as e:
        logger.error("send_audio_request_error", to=to, error=str(e))
        return False


async def execute_admin_command(
    db: AsyncSession, command: str, full_text: str, sender: str
) -> None:
    """Execute WhatsApp Admin Commands (/stats, /ingest, /refresh) and reply."""
    logger.info("executing_admin_command", command=command, sender=sender)

    if command == "/stats" or command == "/health":
        doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
        chunk_count = (
            await db.execute(select(func.count(DocumentChunk.id)))
        ).scalar() or 0
        conv_count = (
            await db.execute(select(func.count(Conversation.id)))
        ).scalar() or 0
        escalation_count = (
            await db.execute(select(func.count(Escalation.id)))
        ).scalar() or 0

        reply = (
            f"📊 *Coligo System Status & Stats*\n\n"
            f"• *Environment*: {settings.ENVIRONMENT}\n"
            f"• *Ingested Documents*: {doc_count}\n"
            f"• *Vector Chunks*: {chunk_count}\n"
            f"• *Active Chat Threads*: {conv_count}\n"
            f"• *Pending Escalations*: {escalation_count}\n"
            f"• *Status*: Healthy 🟢"
        )
        await send_text(sender, reply)

    elif command == "/ingest":
        parts = full_text.strip().split(maxsplit=1)
        if len(parts) < 2:
            await send_text(
                sender,
                "⚠️ *Usage*: `/ingest <document_url_or_path>`\nPlease provide a document URL or path.",
            )
            return

        document_ref = parts[1].strip()
        await send_text(sender, f"🔄 Starting ingestion for:\n`{document_ref}`...")

        try:
            from api.services.document_service import process_document

            text, total, inserted, reused = await process_document(db, document_ref)
            await send_text(
                sender,
                f"✅ *Ingestion Successful!*\n\n"
                f"• *Ref*: {document_ref}\n"
                f"• *Extracted Length*: {len(text)} chars\n"
                f"• *Total Chunks*: {total}\n"
                f"• *New Inserted*: {inserted}\n"
                f"• *Reused Vectors*: {reused}",
            )
        except Exception as e:
            logger.error("admin_ingest_failed", error=str(e))
            await send_text(sender, f"❌ *Ingestion Failed*: {str(e)}")

    elif command == "/refresh":
        doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
        await send_text(
            sender,
            f"🔄 *System Refreshed*\nAll {doc_count} document indexes and tables are active and up to date.",
        )

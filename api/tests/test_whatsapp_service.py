import hashlib
import hmac

import pytest

from api.core.config import settings
from api.schemas.whatsapp import WhatsAppWebhookPayload
from api.services.whatsapp_service import (
    extract_message,
    is_admin_number,
    match_admin_command,
    verify_signature,
)

TEXT_MESSAGE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "102290129340398",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "16505551111",
                            "phone_number_id": "106540352242922",
                        },
                        "contacts": [
                            {
                                "profile": {"name": "Test User"},
                                "wa_id": "919876543210",
                            }
                        ],
                        "messages": [
                            {
                                "from": "919876543210",
                                "id": "wamid.TEST123",
                                "timestamp": "1690000000",
                                "text": {"body": "meri rank 45000 hai OBC category"},
                                "type": "text",
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

STATUS_ONLY_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "102290129340398",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "16505551111",
                            "phone_number_id": "106540352242922",
                        },
                        "statuses": [
                            {
                                "id": "wamid.TEST123",
                                "status": "delivered",
                                "timestamp": "1690000000",
                                "recipient_id": "919876543210",
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}


def test_extract_message_parses_text_message() -> None:
    payload = WhatsAppWebhookPayload.model_validate(TEXT_MESSAGE_PAYLOAD)
    message = extract_message(payload)

    assert message is not None
    assert message.sender == "919876543210"
    assert message.message_type == "text"
    assert message.text == "meri rank 45000 hai OBC category"
    assert message.message_id == "wamid.TEST123"


def test_extract_message_returns_none_for_status_callback() -> None:
    payload = WhatsAppWebhookPayload.model_validate(STATUS_ONLY_PAYLOAD)
    assert extract_message(payload) is None


def test_is_admin_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADMIN_NUMBERS", "919876543210,919999999999")
    assert is_admin_number("919876543210") is True
    assert is_admin_number("911111111111") is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/ingest", "/ingest"),
        ("/stats", "/stats"),
        ("/stats today", "/stats"),
        ("/refresh", "/refresh"),
        ("/health", "/health"),
        ("hello there", None),
        (None, None),
    ],
)
def test_match_admin_command(text: str | None, expected: str | None) -> None:
    assert match_admin_command(text) == expected


def test_verify_signature_accepts_correct_signature() -> None:
    body = b'{"object": "whatsapp_business_account"}'
    secret = "test-app-secret"
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, signature, secret) is True


def test_verify_signature_rejects_tampered_body() -> None:
    body = b'{"object": "whatsapp_business_account"}'
    secret = "test-app-secret"
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    tampered_body = b'{"object": "tampered"}'
    assert verify_signature(tampered_body, signature, secret) is False


def test_verify_signature_rejects_missing_header() -> None:
    assert verify_signature(b"{}", None, "secret") is False

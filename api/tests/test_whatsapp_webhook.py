import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from api.core.config import settings
from api.tests.test_whatsapp_service import STATUS_ONLY_PAYLOAD, TEXT_MESSAGE_PAYLOAD


def test_webhook_verification_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test-verify-token")
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 200
    assert response.text == "12345"


def test_webhook_verification_wrong_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test-verify-token")
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 403


def test_webhook_post_text_message_no_app_secret_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "")
    response = client.post("/webhook", json=TEXT_MESSAGE_PAYLOAD)
    assert response.status_code == 200
    assert response.json() == {"status": "received"}


def test_webhook_post_status_only_payload_is_ignored(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "")
    response = client.post("/webhook", json=STATUS_ONLY_PAYLOAD)
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_webhook_post_valid_signature_is_accepted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "test-app-secret"
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", secret)
    body = json.dumps(TEXT_MESSAGE_PAYLOAD).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "received"}


def test_webhook_post_invalid_signature_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "test-app-secret")
    response = client.post(
        "/webhook",
        json=TEXT_MESSAGE_PAYLOAD,
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert response.status_code == 401


def test_webhook_post_from_admin_number_still_succeeds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Full pipeline doesn't crash for an admin sender.

    The admin-vs-student *decision* logic itself is unit-tested directly in
    test_whatsapp_service.py::test_is_admin_number — the response body is
    intentionally identical either way in this phase (no reply is sent yet).
    """
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "")
    monkeypatch.setattr(settings, "ADMIN_NUMBERS", "919876543210")
    response = client.post("/webhook", json=TEXT_MESSAGE_PAYLOAD)
    assert response.status_code == 200
    assert response.json() == {"status": "received"}

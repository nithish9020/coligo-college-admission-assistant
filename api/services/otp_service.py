"""WhatsApp OTP Authentication Service for Student Portal."""

import re
import secrets
import time
from typing import Any, Optional

from api.core.logging import get_logger
from api.services.whatsapp_service import send_text

logger = get_logger(__name__)

# Constants
OTP_TTL_SECONDS = 300  # 5 minutes
OTP_COOLDOWN_SECONDS = 45  # 45 seconds before resending allowed
MAX_VERIFICATION_ATTEMPTS = 3

# In-memory store:
# { normalized_phone: { "otp": str, "expires_at": float, "attempts": int } }
_OTP_CACHE: dict[str, dict[str, Any]] = {}


def normalize_phone(phone: str) -> str:
    """Normalize phone number to clean E.164 without '+' prefix (e.g. 919876543210)."""
    clean = re.sub(r"[^\d]", "", phone.strip())
    if len(clean) == 10:
        # Default 10-digit Indian mobile number
        return f"91{clean}"
    if clean.startswith("0") and len(clean) == 11:
        return f"91{clean[1:]}"
    return clean


def is_valid_phone(phone: str) -> bool:
    """Validate normalized phone string."""
    norm = normalize_phone(phone)
    # Most international WhatsApp numbers are 10 to 15 digits
    return 10 <= len(norm) <= 15


async def send_whatsapp_otp(phone: str) -> tuple[bool, str, int]:
    """Generate and dispatch a 6-digit verification code to student's WhatsApp.

    Returns:
        tuple[bool, str, int]: (success, status_message, cooldown_or_expires_in)
    """
    norm_phone = normalize_phone(phone)
    if not is_valid_phone(norm_phone):
        return (
            False,
            "Invalid phone number format. Please provide a valid mobile number.",
            0,
        )

    now = time.time()
    existing = _OTP_CACHE.get(norm_phone)

    # Check resend cooldown
    if existing:
        time_since_last = now - existing.get("sent_at", 0)
        if time_since_last < OTP_COOLDOWN_SECONDS:
            remaining = int(OTP_COOLDOWN_SECONDS - time_since_last)
            return (
                False,
                f"Please wait {remaining} seconds before requesting a new OTP.",
                remaining,
            )

    # Generate cryptographically secure 6-digit numeric OTP
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = now + OTP_TTL_SECONDS

    _OTP_CACHE[norm_phone] = {
        "otp": code,
        "expires_at": expires_at,
        "attempts": 0,
        "sent_at": now,
    }

    message = (
        "*Coligo Admissions Portal — Login Code*\n\n"
        f"Your 6-digit verification code is: *{code}*\n\n"
        "Valid for 5 minutes.\n"
        "Do not share this code with anyone."
    )

    try:
        sent = await send_text(to=norm_phone, body=message)
        logger.info(
            "whatsapp_otp_dispatched",
            phone=norm_phone,
            sent_status=sent,
            expires_in=OTP_TTL_SECONDS,
        )
        return (
            True,
            f"Verification OTP sent to WhatsApp number +{norm_phone}.",
            OTP_TTL_SECONDS,
        )
    except Exception as e:
        logger.error("whatsapp_otp_send_failed", phone=norm_phone, error=str(e))
        return (
            False,
            "Failed to send WhatsApp message. Please check the number and try again.",
            0,
        )


def verify_whatsapp_otp(phone: str, code: str) -> tuple[bool, str]:
    """Verify submitted OTP code against active record.

    Returns:
        tuple[bool, str]: (verified, message)
    """
    norm_phone = normalize_phone(phone)
    record = _OTP_CACHE.get(norm_phone)

    if not record:
        return (
            False,
            "No active OTP request found. Please request a new verification code.",
        )

    now = time.time()
    if now > record["expires_at"]:
        _OTP_CACHE.pop(norm_phone, None)
        return False, "Verification code has expired. Please request a new code."

    if record["attempts"] >= MAX_VERIFICATION_ATTEMPTS:
        _OTP_CACHE.pop(norm_phone, None)
        return (
            False,
            "Too many incorrect attempts. Please request a new verification code.",
        )

    record["attempts"] += 1
    input_code = code.strip()

    if input_code == record["otp"]:
        # Successful verification: remove OTP to prevent replay attacks
        _OTP_CACHE.pop(norm_phone, None)
        logger.info("whatsapp_otp_verified_successfully", phone=norm_phone)
        return True, "Phone number verified successfully."

    remaining = MAX_VERIFICATION_ATTEMPTS - record["attempts"]
    return (
        False,
        f"Incorrect verification code. {remaining} attempt(s) remaining.",
    )


def get_active_otp_details(phone: str) -> Optional[dict[str, Any]]:
    """Helper to inspect active OTP status for tests and rate limits."""
    norm_phone = normalize_phone(phone)
    return _OTP_CACHE.get(norm_phone)

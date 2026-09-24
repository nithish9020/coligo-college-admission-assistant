from typing import Any, cast

import httpx

from api.core.config import settings
from api.core.logging import get_logger

logger = get_logger(__name__)


async def download_whatsapp_media(media_id: str) -> tuple[bytes, str] | None:
    """Fetch media binary data and mime type from Meta WhatsApp Cloud API."""
    if not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("whatsapp_access_token_missing_for_media_download")
        return None

    meta_url = (
        f"https://graph.facebook.com/" f"{settings.WHATSAPP_API_VERSION}/{media_id}"
    )
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # 1. Get media direct download URL
            res = await client.get(meta_url, headers=headers)
            if res.status_code >= 400:
                logger.error(
                    "meta_media_url_fetch_failed",
                    status=res.status_code,
                    body=res.text,
                )
                return None

            data = res.json()
            download_url = data.get("url")
            mime_type = data.get("mime_type", "audio/ogg")
            if not download_url:
                return None

            # 2. Download binary bytes
            audio_res = await client.get(download_url, headers=headers)
            if audio_res.status_code >= 400:
                logger.error(
                    "media_binary_download_failed", status=audio_res.status_code
                )
                return None

            return audio_res.content, mime_type
    except Exception as e:
        logger.error(
            "download_whatsapp_media_exception",
            media_id=media_id,
            error=str(e),
        )
        return None


async def transcribe_with_groq_whisper(
    audio_bytes: bytes, filename: str = "voice.ogg"
) -> str | None:
    """Transcribe audio using Groq Whisper-large-v3 at ~200x real-time."""
    if not settings.GROQ_API_KEY:
        return None

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    files = {"file": (filename, audio_bytes, "audio/ogg")}
    data = {
        "model": "whisper-large-v3",
        "prompt": "TNEA admissions, cutoffs, marks, PSG, SKCET, CIT, Anna Univ.",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=headers, files=files, data=data)
            if res.status_code >= 400:
                logger.warning(
                    "groq_whisper_failed",
                    status=res.status_code,
                    body=res.text,
                )
                return None
            result: dict[str, Any] = res.json()
            raw_text = result.get("text")
            if raw_text is not None and isinstance(raw_text, str):
                transcript = raw_text.strip()
                logger.info("groq_whisper_succeeded", length=len(transcript))
                return transcript
            return None
    except Exception as e:
        logger.error("groq_whisper_exception", error=str(e))
        return None


async def transcribe_with_gemini(
    audio_bytes: bytes, mime_type: str = "audio/ogg"
) -> str | None:
    """Fallback: Transcribe audio using Google Gemini multimodal capabilities."""
    if not settings.GEMINI_API_KEY:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        clean_mime = mime_type.split(";")[0].strip() or "audio/ogg"

        prompt = (
            "Listen to this WhatsApp voice message from a student or parent. "
            "Accurately transcribe the Tamil or English speech into text. "
            "Output ONLY the transcribed words. Do not add any preamble."
        )

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=cast(Any, [audio_part, prompt]),
        )

        if response and response.text:
            text = response.text.strip().strip('"').strip("'")
            logger.info("gemini_audio_transcription_succeeded", length=len(text))
            return text
        return None
    except Exception as e:
        logger.error("gemini_audio_transcription_failed", error=str(e))
        return None


async def transcribe_audio_message(media_id: str) -> str | None:
    """End-to-end voice note transcription via Groq Whisper with Gemini fallback."""
    media_data = await download_whatsapp_media(media_id)
    if not media_data:
        return None

    audio_bytes, mime_type = media_data

    # 1. Try Groq Whisper (ultra-fast ~300ms)
    transcript = await transcribe_with_groq_whisper(audio_bytes)
    if transcript:
        return transcript

    # 2. Fallback to Gemini
    transcript = await transcribe_with_gemini(audio_bytes, mime_type)
    return transcript

"""Audio and voice note processing service for Meta WhatsApp Cloud API."""

from typing import Any, cast

import httpx

from api.core.config import settings
from api.core.logging import get_logger

logger = get_logger(__name__)

WHISPER_NOISE_ARTIFACTS = {
    "you",
    "thank you",
    "thank you.",
    "thanks for watching",
    "thanks for watching!",
    "subtitles by",
    "amara.org",
    "transcript:",
    "subscribe",
    "bye",
    "bye.",
    "hello",
}


def _detect_audio_extension_and_mime(mime_type: str) -> tuple[str, str]:
    """Extract file extension and canonical MIME type from WhatsApp media header."""
    clean = mime_type.split(";")[0].strip().lower() or "audio/ogg"
    if "mp4" in clean or "m4a" in clean:
        return "m4a", "audio/mp4"
    if "wav" in clean:
        return "wav", "audio/wav"
    if "amr" in clean:
        return "amr", "audio/amr"
    if "aac" in clean:
        return "aac", "audio/aac"
    if "mpeg" in clean or "mp3" in clean:
        return "mp3", "audio/mpeg"
    return "ogg", "audio/ogg"


async def download_whatsapp_media(media_id: str) -> tuple[bytes, str] | None:
    """Fetch media binary data and mime type from Meta WhatsApp Cloud API."""
    if not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("whatsapp_access_token_missing_for_media_download")
        return None

    meta_url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        # Crucial: follow_redirects=True to follow Meta's CDN redirect
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            # 1. Get media direct download URL
            res = await client.get(meta_url, headers=headers)
            if res.status_code >= 400:
                logger.error(
                    "meta_media_url_fetch_failed",
                    status=res.status_code,
                    body=res.text,
                    media_id=media_id,
                )
                return None

            data = res.json()
            download_url = data.get("url")
            mime_type = data.get("mime_type", "audio/ogg")
            if not download_url:
                logger.error("meta_media_download_url_empty", media_id=media_id)
                return None

            # 2. Download binary bytes
            audio_res = await client.get(download_url, headers=headers)
            if audio_res.status_code >= 400:
                logger.error(
                    "media_binary_download_failed",
                    status=audio_res.status_code,
                    media_id=media_id,
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
    audio_bytes: bytes,
    filename: str = "voice.ogg",
    content_type: str = "audio/ogg",
) -> str | None:
    """Transcribe audio using Groq Whisper-large-v3 at ~200x real-time."""
    if not settings.GROQ_API_KEY:
        return None

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    files = {"file": (filename, audio_bytes, content_type)}
    data = {
        "model": "whisper-large-v3",
        "prompt": (
            "Tamil Nadu Engineering Admissions, TNEA, cutoff mark, SKCET, PSG, "
            "CIT, KCT, Coimbatore, community OC BC MBC SC ST, CSE, ECE, AI DS, "
            "fees, hostel, placements, Sri Krishna College, அண்ணா பல்கலைக்கழகம், கவுன்சிலிங்."
        ),
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
                # Filter out Whisper near-silent hallucination artifacts
                if transcript.lower() in WHISPER_NOISE_ARTIFACTS or len(transcript) < 3:
                    logger.info("groq_whisper_noise_filtered", raw=transcript)
                    return None
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
            "You are a specialized audio transcriber for Tamil Nadu Engineering "
            "Admissions (TNEA) counselling. Listen to this WhatsApp voice message "
            "spoken by a student or parent. The speech may be in Tamil (தமிழ்), "
            "English, or Tanglish (spoken Tamil mixed with English). "
            "Accurately transcribe the spoken query into text. "
            "Output ONLY the transcribed words. Do not add any preamble, quotes, "
            "or explanations."
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

    audio_bytes, raw_mime = media_data
    ext, clean_mime = _detect_audio_extension_and_mime(raw_mime)
    filename = f"voice.{ext}"

    # 1. Try Groq Whisper (ultra-fast ~300ms)
    transcript = await transcribe_with_groq_whisper(
        audio_bytes, filename=filename, content_type=clean_mime
    )
    if transcript:
        return transcript

    # 2. Fallback to Gemini Multimodal Audio
    transcript = await transcribe_with_gemini(audio_bytes, clean_mime)
    return transcript

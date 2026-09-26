"""Tamil and Indian English neural text-to-speech service using Edge-TTS."""

import re
from typing import Optional

import edge_tts

from api.core.config import settings
from api.core.logging import get_logger
from api.services.whatsapp_service import send_audio, upload_media

logger = get_logger(__name__)

# Unicode block for Tamil characters: U+0B80 to U+0BFF
TAMIL_CHAR_PATTERN = re.compile(r"[\u0B80-\u0BFF]")


def contains_tamil(text: str) -> bool:
    """Return True if the text contains Tamil unicode characters."""
    return bool(TAMIL_CHAR_PATTERN.search(text))


def clean_text_for_speech(text: str) -> str:
    """Strip markdown formatting, links, and emojis for smooth neural speech."""
    # Remove markdown links [label](url) -> label
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove raw URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove bold, italics, strikethrough, backticks
    cleaned = re.sub(r"[*_~`]", "", cleaned)
    # Remove list bullets, markdown headers, and blockquotes
    cleaned = re.sub(r"^[ \t]*[#•\-*+>][ \t]*", "", cleaned, flags=re.MULTILINE)
    # Remove emojis and special decorative symbols
    cleaned = re.sub(
        r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]",
        "",
        cleaned,
    )
    # Collapse multiple whitespaces and newlines
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def prepare_spoken_summary(text: str, is_tamil: bool) -> str:
    """Create a concise, conversational spoken message for audio delivery.

    Students prefer a quick 10-15 second voice overview rather than an
    exhausting reading of tables and 20 cutoff rows.
    """
    cleaned = clean_text_for_speech(text)

    # If the message is already short and conversational, speak it directly
    if len(cleaned) <= 280:
        return cleaned

    # For longer analytical or tabular responses, generate a polished spoken summary
    if is_tamil:
        return (
            "வணக்கம்! உங்கள் சேர்க்கை மற்றும் கட்-ஆஃப் விவரங்களை "
            "கீழே உள்ள வாட்ஸ்அப் செய்தியில் விரிவாக அனுப்பியுள்ளேன். "
            "பரிந்துரைக்கப்பட்ட கல்லூரிகள் மற்றும் விருப்பப் பட்டியலை பார்க்கவும்!"
        )

    return (
        "Hello! I have generated the admission analysis and cutoff details. "
        "The complete structured choice list and recommendations have been sent in "
        "the text message below. Feel free to ask any follow-up questions!"
    )


async def synthesize_speech(
    text: str,
    voice: Optional[str] = None,
    is_tamil: Optional[bool] = None,
) -> bytes | None:
    """Synthesize text into natural Tamil or Indian English neural audio bytes."""
    if not text or not text.strip():
        return None

    if is_tamil is None:
        is_tamil = contains_tamil(text)
    spoken_text = prepare_spoken_summary(text, is_tamil=is_tamil)

    if not voice:
        voice = (
            settings.DEFAULT_TAMIL_VOICE if is_tamil else settings.DEFAULT_ENGLISH_VOICE
        )

    logger.info(
        "synthesizing_speech_start",
        voice=voice,
        char_count=len(spoken_text),
        is_tamil=is_tamil,
    )

    try:
        communicate = edge_tts.Communicate(spoken_text, voice)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])

        audio_bytes = b"".join(chunks)
        logger.info(
            "synthesizing_speech_succeeded",
            voice=voice,
            byte_length=len(audio_bytes),
        )
        return audio_bytes
    except Exception as e:
        logger.error("synthesizing_speech_failed", voice=voice, error=str(e))
        return None


async def send_voice_reply(
    to: str,
    answer_text: str,
    is_tamil: Optional[bool] = None,
) -> bool:
    """Synthesize spoken response, upload to WhatsApp Cloud API, and send voice note."""
    if not settings.ENABLE_VOICE_RESPONSES:
        return False

    audio_bytes = await synthesize_speech(answer_text, is_tamil=is_tamil)
    if not audio_bytes:
        return False

    media_id = await upload_media(
        file_bytes=audio_bytes,
        mime_type="audio/ogg",
        filename="voice_reply.ogg",
    )
    if not media_id:
        return False

    sent = await send_audio(to=to, audio_id_or_url=media_id, is_id=True)
    if sent:
        logger.info("voice_reply_delivered_successfully", to=to, media_id=media_id)
    return sent

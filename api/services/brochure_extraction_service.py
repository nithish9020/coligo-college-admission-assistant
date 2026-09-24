import json
from typing import Any, cast

from openai import APIError as OpenAIAPIError
from openai import AsyncOpenAI, OpenAIError

from api.core.config import settings
from api.core.exceptions import BrochureExtractionError
from api.core.logging import get_logger
from api.services.pdf_extractor import extract_text_from_pdf_bytes

logger = get_logger(__name__)

# Brochures are marketing PDFs, not full catalogs — a few thousand words is
# plenty of context and keeps the OpenAI call fast and cheap.
MAX_CHARS = 20000

SYSTEM_PROMPT = (
    "You are an assistant that reads a college admission brochure and extracts "
    "structured facts about the college, the courses it offers, and its campus "
    "facilities. Only include information that is explicitly stated in the "
    "text. Leave a field null instead of guessing or inventing values, and do "
    "not fabricate courses or facilities that are not mentioned in the text."
)

_NULLABLE_STRING = {"type": ["string", "null"]}
_NULLABLE_INTEGER = {"type": ["integer", "null"]}

_COLLEGE_PROFILE_PROPERTIES = {
    "college_type": _NULLABLE_STRING,
    "established_year": _NULLABLE_INTEGER,
    "affiliated_university": _NULLABLE_STRING,
    "about": _NULLABLE_STRING,
    "contact_person": _NULLABLE_STRING,
    "contact_email": _NULLABLE_STRING,
    "contact_phone": _NULLABLE_STRING,
    "address": _NULLABLE_STRING,
    "city": _NULLABLE_STRING,
    "state": _NULLABLE_STRING,
    "pincode": _NULLABLE_STRING,
    "website": _NULLABLE_STRING,
    "facebook": _NULLABLE_STRING,
    "twitter": _NULLABLE_STRING,
    "linkedin": _NULLABLE_STRING,
    "instagram": _NULLABLE_STRING,
    "accreditation": _NULLABLE_STRING,
}

_PROGRAM_LEVELS = ["UG", "PG", "Diploma", "PhD", None]

_COURSE_PROPERTIES = {
    "program_level": {"type": ["string", "null"], "enum": _PROGRAM_LEVELS},
    "course_name": {"type": "string"},
    "course_code": _NULLABLE_STRING,
    "duration": _NULLABLE_STRING,
    "intake_capacity": _NULLABLE_INTEGER,
    "department": _NULLABLE_STRING,
    "eligibility": _NULLABLE_STRING,
    "fees": _NULLABLE_STRING,
    "course_details": _NULLABLE_STRING,
    "career_opportunities": _NULLABLE_STRING,
}

_FACILITY_PROPERTIES = {
    "name": {"type": "string"},
    "description": _NULLABLE_STRING,
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "college_profile": {
            "type": "object",
            "properties": _COLLEGE_PROFILE_PROPERTIES,
            "required": list(_COLLEGE_PROFILE_PROPERTIES),
            "additionalProperties": False,
        },
        "courses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": _COURSE_PROPERTIES,
                "required": list(_COURSE_PROPERTIES),
                "additionalProperties": False,
            },
        },
        "facilities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": _FACILITY_PROPERTIES,
                "required": list(_FACILITY_PROPERTIES),
                "additionalProperties": False,
            },
        },
    },
    "required": ["college_profile", "courses", "facilities"],
    "additionalProperties": False,
}


async def extract_brochure_details(pdf_bytes: bytes) -> dict:
    """Extract structured college/course/facility details from a brochure PDF.

    Raises:
        CorruptedDocumentError / EmptyDocumentTextError: from PDF text extraction.
        BrochureExtractionError: if OpenAI is unconfigured, unreachable, or
            returns output that cannot be parsed as the expected JSON shape.
    """
    if not settings.OPENAI_API_KEY:
        logger.error("openai_api_key_missing_for_brochure_extraction")
        raise BrochureExtractionError(
            "OPENAI_API_KEY is not configured in the application environment."
        )

    text = extract_text_from_pdf_bytes(pdf_bytes)[:MAX_CHARS]

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    logger.debug("sending_brochure_to_openai", model=settings.OPENAI_MODEL)

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format=cast(
                Any,
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "brochure_extraction",
                        "schema": EXTRACTION_SCHEMA,
                        "strict": True,
                    },
                },
            ),
        )
    except OpenAIAPIError as e:
        logger.error("openai_brochure_extraction_failed", error=str(e))
        raise BrochureExtractionError(f"OpenAI extraction request failed: {e}") from e
    except OpenAIError as e:
        logger.error("openai_brochure_extraction_error", error=str(e))
        raise BrochureExtractionError(f"OpenAI extraction failed: {e}") from e

    content = response.choices[0].message.content if response.choices else None
    if not content:
        logger.warning("openai_brochure_extraction_empty_response")
        raise BrochureExtractionError("OpenAI returned an empty extraction response.")

    try:
        result = cast(dict[str, Any], json.loads(content))
    except json.JSONDecodeError as e:
        logger.error("openai_brochure_extraction_unparsable", error=str(e))
        raise BrochureExtractionError(
            "OpenAI returned a response that could not be parsed as JSON."
        ) from e

    logger.info(
        "brochure_extraction_completed",
        course_count=len(result.get("courses") or []),
        facility_count=len(result.get("facilities") or []),
    )
    return result

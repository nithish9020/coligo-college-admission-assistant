"""Thin wrapper around the Coligo FastAPI backend for the Streamlit admin portal."""

import os
from typing import Any, cast

import requests


def _resolve_api_base_url() -> str:
    for env_key in ("COLIGO_API_BASE_URL", "API_BASE_URL"):
        val = os.environ.get(env_key)
        if val:
            return val.rstrip("/")
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            for key in ("COLIGO_API_BASE_URL", "API_BASE_URL", "coligo_api_base_url"):
                if key in st.secrets:
                    return str(st.secrets[key]).rstrip("/")
    except Exception:
        pass
    return "http://localhost:8000"


API_BASE_URL = _resolve_api_base_url()
REQUEST_TIMEOUT = 30


class APIError(Exception):
    """Raised when the backend returns a non-2xx response."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _auth_headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _handle_response(resp: requests.Response) -> Any:
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text or f"Request failed with status {resp.status_code}"
        raise APIError(detail, resp.status_code)
    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def _request(
    method: str,
    path: str,
    token: str | None = None,
    timeout: int = REQUEST_TIMEOUT,
    **kwargs: Any,
) -> Any:
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.request(
            method, url, headers=_auth_headers(token), timeout=timeout, **kwargs
        )
    except requests.exceptions.ConnectionError as e:
        raise APIError(
            f"Could not reach the backend API at {API_BASE_URL}. "
            "Is the FastAPI server running?"
        ) from e
    except requests.exceptions.Timeout as e:
        raise APIError("The backend API took too long to respond.") from e
    return _handle_response(resp)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def signup_college(college_name: str, email: str, password: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request(
            "POST",
            "/auth/signup",
            json={"college_name": college_name, "email": email, "password": password},
        ),
    )


def login(email: str, password: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request("POST", "/auth/login", json={"email": email, "password": password}),
    )


def get_me(token: str) -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", "/auth/me", token=token))


# ---------------------------------------------------------------------------
# College profile
# ---------------------------------------------------------------------------


def get_my_profile(token: str) -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", "/colleges/me", token=token))


def update_my_profile(token: str, data: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], _request("PUT", "/colleges/me", token=token, json=data))


def upload_logo(
    token: str, filename: str, content: bytes, content_type: str
) -> dict[str, Any]:
    files = {"file": (filename, content, content_type)}
    return cast(
        dict[str, Any],
        _request("POST", "/colleges/me/logo", token=token, files=files),
    )


def list_colleges(token: str) -> list[Any]:
    return cast(list[Any], _request("GET", "/colleges", token=token))


def get_college_detail(token: str, college_id: int) -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", f"/colleges/{college_id}", token=token))


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------


def list_courses(token: str, college_id: int | None = None) -> list[Any]:
    params = {"college_id": college_id} if college_id is not None else None
    return cast(list[Any], _request("GET", "/courses", token=token, params=params))


def create_course(token: str, data: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], _request("POST", "/courses", token=token, json=data))


def update_course(token: str, course_id: int, data: dict[str, Any]) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request("PUT", f"/courses/{course_id}", token=token, json=data),
    )


def delete_course(token: str, course_id: int) -> None:
    _request("DELETE", f"/courses/{course_id}", token=token)


# ---------------------------------------------------------------------------
# Facilities / Infrastructure
# ---------------------------------------------------------------------------


def list_facilities(token: str, college_id: int | None = None) -> list[Any]:
    params = {"college_id": college_id} if college_id is not None else None
    return cast(list[Any], _request("GET", "/facilities", token=token, params=params))


def create_facility(token: str, data: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], _request("POST", "/facilities", token=token, json=data))


def update_facility(
    token: str, facility_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request("PUT", f"/facilities/{facility_id}", token=token, json=data),
    )


def delete_facility(token: str, facility_id: int) -> None:
    _request("DELETE", f"/facilities/{facility_id}", token=token)


# ---------------------------------------------------------------------------
# Brochures
# ---------------------------------------------------------------------------


def list_brochures(token: str, college_id: int | None = None) -> list[Any]:
    params = {"college_id": college_id} if college_id is not None else None
    return cast(list[Any], _request("GET", "/brochures", token=token, params=params))


def upload_brochure(
    token: str, title: str, category: str | None, filename: str, content: bytes
) -> dict[str, Any]:
    files = {"file": (filename, content, "application/pdf")}
    data = {"title": title, "category": category or ""}
    return cast(
        dict[str, Any],
        _request("POST", "/brochures", token=token, data=data, files=files),
    )


def update_brochure(
    token: str, brochure_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request("PUT", f"/brochures/{brochure_id}", token=token, json=data),
    )


def delete_brochure(token: str, brochure_id: int) -> None:
    _request("DELETE", f"/brochures/{brochure_id}", token=token)


def extract_brochure(token: str, brochure_id: int) -> dict[str, Any]:
    """Runs OpenAI extraction over an uploaded brochure. Slower than a normal
    request (parses a PDF + one LLM call), so it gets a longer timeout."""
    return cast(
        dict[str, Any],
        _request("POST", f"/brochures/{brochure_id}/extract", token=token, timeout=90),
    )


def apply_brochure_extraction(
    token: str, brochure_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request(
            "POST",
            f"/brochures/{brochure_id}/apply-extraction",
            token=token,
            json=payload,
        ),
    )


def download_brochure(token: str, brochure_id: int) -> bytes:
    url = f"{API_BASE_URL}/brochures/{brochure_id}/download"
    try:
        resp = requests.get(url, headers=_auth_headers(token), timeout=REQUEST_TIMEOUT)
    except requests.exceptions.ConnectionError as e:
        raise APIError(f"Could not reach the backend API at {API_BASE_URL}.") from e
    if resp.status_code >= 400:
        raise APIError("Failed to download brochure", resp.status_code)
    return resp.content


# ---------------------------------------------------------------------------
# Documents & Ingestion (Knowledge Base)
# ---------------------------------------------------------------------------


def list_documents(token: str | None = None) -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", "/documents", token=token))


def delete_document(token: str | None, document_id: int) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request("DELETE", f"/documents/{document_id}", token=token),
    )


def scrape_college(
    token: str | None, college_name: str, urls: list[str]
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request(
            "POST",
            "/documents/scrape",
            token=token,
            json={"college_name": college_name, "urls": urls},
            timeout=120,
        ),
    )


def process_document(document_ref: str, token: str | None = None) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request(
            "POST",
            "/documents/process",
            token=token,
            json={"document_ref": document_ref},
            timeout=180,
        ),
    )


# ---------------------------------------------------------------------------
# Human Escalations
# ---------------------------------------------------------------------------


def list_escalations(token: str | None = None) -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", "/escalations", token=token))


def resolve_escalation(token: str | None, escalation_id: int) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request("PATCH", f"/escalations/{escalation_id}/resolve", token=token),
    )


def reply_escalation(
    token: str | None,
    escalation_id: int,
    message: str,
    resolve: bool = True,
    send_whatsapp: bool = True,
) -> dict[str, Any]:
    """Send counselor live reply to student and optionally resolve ticket."""
    return cast(
        dict[str, Any],
        _request(
            "POST",
            f"/escalations/{escalation_id}/reply",
            token=token,
            json={
                "message": message,
                "resolve": resolve,
                "send_whatsapp": send_whatsapp,
            },
        ),
    )


def update_escalation_status(
    token: str | None, escalation_id: int, status: str
) -> dict[str, Any]:
    """Update status of escalation ticket (e.g. pending, in_progress, resolved)."""
    return cast(
        dict[str, Any],
        _request(
            "PATCH",
            f"/escalations/{escalation_id}/status",
            token=token,
            json={"status": status},
        ),
    )


# ---------------------------------------------------------------------------
# AI Counseling Assistant Chat
# ---------------------------------------------------------------------------


def send_chat_message(message: str, session_id: str | None = None) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request(
            "POST",
            "/chat",
            json={"message": message, "session_id": session_id},
            timeout=60,
        ),
    )


# ---------------------------------------------------------------------------
# Analytics & System Health
# ---------------------------------------------------------------------------


def get_analytics_summary(token: str | None = None) -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", "/analytics/summary", token=token))


def list_conversations(
    token: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    return cast(
        list[dict[str, Any]],
        _request(
            "GET", "/analytics/conversations", token=token, params={"limit": limit}
        ),
    )


def get_conversation(token: str | None, conversation_id: int) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request("GET", f"/analytics/conversations/{conversation_id}", token=token),
    )


def get_health() -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", "/health"))


def get_detailed_health() -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", "/health/detailed"))


# ---------------------------------------------------------------------------
# TNEA Cutoffs & Choice Filling Generator
# ---------------------------------------------------------------------------


def get_choice_recommendations(
    cutoff: float,
    community: str,
    branches: list[str] | None = None,
    colleges: list[str] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"cutoff": cutoff, "community": community}
    if branches:
        params["branches"] = ",".join(branches)
    if colleges:
        params["colleges"] = ",".join(colleges)
    return cast(
        dict[str, Any],
        _request("GET", "/cutoffs/recommendations", token=token, params=params),
    )


def search_cutoffs(
    college: str | None = None,
    branch: str | None = None,
    community: str | None = None,
    limit: int = 50,
    token: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit}
    if college:
        params["college"] = college
    if branch:
        params["branch"] = branch
    if community:
        params["community"] = community
    return cast(
        list[dict[str, Any]],
        _request("GET", "/cutoffs/search", token=token, params=params),
    )

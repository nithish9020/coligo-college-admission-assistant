"""Thin wrapper around the Coligo FastAPI backend for the Streamlit admin portal."""

import os
from typing import Any, cast

import requests


def _resolve_api_base_url() -> str:
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            for key in ("COLIGO_API_BASE_URL", "API_BASE_URL", "coligo_api_base_url"):
                if key in st.secrets:
                    return str(st.secrets[key]).rstrip("/")
    except Exception:
        pass
    for env_key in ("COLIGO_API_BASE_URL", "API_BASE_URL"):
        val = os.environ.get(env_key)
        if val:
            return val.rstrip("/")
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

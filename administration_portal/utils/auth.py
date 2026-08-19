"""Session-state helpers for authentication and navigation state.

Login persistence: on successful login we mirror the session into a
browser cookie (7 days) so a closed/reopened tab restores the session
without a fresh login. The cookie is only cleared on explicit logout.
"""

import json

import streamlit as st
import streamlit.components.v1 as components

REMEMBER_COOKIE = "coligo_session"
REMEMBER_DAYS = 7


def init_session_state() -> None:
    defaults = {
        "token": None,
        "role": None,  # "admin" or "college"
        "college_id": None,
        "college_name": None,
        "email": None,
        "page": "login",  # login | signup | college_app | admin_app
        "nav": "Dashboard",
        "viewing_college_id": None,  # admin drill-down into a specific college
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _set_remember_cookie(payload: dict) -> None:
    value = json.dumps(payload).replace("\\", "\\\\").replace("`", "\\`")
    max_age = REMEMBER_DAYS * 24 * 60 * 60
    components.html(
        f"""
        <script>
        document.cookie = "{REMEMBER_COOKIE}=" + encodeURIComponent(`{value}`)
            + "; path=/; max-age={max_age}; SameSite=Lax";
        </script>
        """,
        height=0,
        width=0,
    )


def _clear_remember_cookie() -> None:
    components.html(
        f"""
        <script>
        document.cookie = "{REMEMBER_COOKIE}=; path=/; max-age=0; SameSite=Lax";
        </script>
        """,
        height=0,
        width=0,
    )


def restore_session_from_cookie() -> None:
    """Repopulate session state from the remember-me cookie, if present.

    Runs on every app boot before the auth check so a browser restart
    (new Streamlit session) still lands the user in their last app instead
    of the login page, as long as the cookie hasn't expired or been cleared
    by logout.
    """
    if st.session_state.get("token"):
        return
    raw = st.context.cookies.get(REMEMBER_COOKIE)
    if not raw:
        return
    try:
        payload = json.loads(raw)
        token = payload["access_token"]
        role = payload["role"]
    except (ValueError, KeyError, TypeError):
        return
    st.session_state.token = token
    st.session_state.role = role
    st.session_state.college_id = payload.get("college_id")
    st.session_state.college_name = payload.get("college_name")
    st.session_state.email = payload.get("email")
    st.session_state.page = "admin_app" if role == "admin" else "college_app"


def log_in(token_response: dict, email: str | None = None) -> None:
    st.session_state.token = token_response["access_token"]
    st.session_state.role = token_response["role"]
    st.session_state.college_id = token_response.get("college_id")
    st.session_state.college_name = token_response.get("college_name")
    st.session_state.email = email
    st.session_state.page = (
        "admin_app" if token_response["role"] == "admin" else "college_app"
    )
    st.session_state.nav = "Dashboard"

    _set_remember_cookie(
        {
            "access_token": st.session_state.token,
            "role": st.session_state.role,
            "college_id": st.session_state.college_id,
            "college_name": st.session_state.college_name,
            "email": st.session_state.email,
        }
    )


def log_out() -> None:
    for key in (
        "token",
        "role",
        "college_id",
        "college_name",
        "email",
        "viewing_college_id",
    ):
        st.session_state[key] = None
    st.session_state.page = "login"
    st.session_state.nav = "Dashboard"
    _clear_remember_cookie()


def is_authenticated() -> bool:
    return st.session_state.get("token") is not None


def require_role(role: str) -> bool:
    return is_authenticated() and st.session_state.get("role") == role

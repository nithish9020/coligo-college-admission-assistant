"""Session-state helpers for authentication and navigation state."""

import streamlit as st


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


def log_in(token_response: dict) -> None:
    st.session_state.token = token_response["access_token"]
    st.session_state.role = token_response["role"]
    st.session_state.college_id = token_response.get("college_id")
    st.session_state.college_name = token_response.get("college_name")
    st.session_state.page = (
        "admin_app" if token_response["role"] == "admin" else "college_app"
    )
    st.session_state.nav = "Dashboard"


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


def is_authenticated() -> bool:
    return st.session_state.get("token") is not None


def require_role(role: str) -> bool:
    return is_authenticated() and st.session_state.get("role") == role

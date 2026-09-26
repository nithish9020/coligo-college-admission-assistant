import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st
from utils.auth import log_out
from utils.styling import PRIMARY_BRIGHT, avatar_html

from api.services.student_profile_service import (
    get_student_profile,
    update_student_profile,
)

STUDENT_NAV = [
    ("AI Admissions Chatbot", ""),
    ("Cutoff Visualizer & Graphs", ""),
    ("Head-to-Head College Comparator", ""),
    ("Seat Matrix & Quota Pie Charts", ""),
    ("Placement & Recruiter Analytics", ""),
    ("3-Tier Choice Sheet Builder", ""),
    ("TNEA Rank & Round Predictor", ""),
    ("Upward Movement Simulator", ""),
]

COLLEGE_NAV = [
    ("Dashboard", ""),
    ("College Profile", ""),
    ("Courses", ""),
    ("Infrastructure", ""),
    ("Brochures", ""),
    ("Choice Filling", ""),
    ("Counselor Chat", ""),
]

ADMIN_NAV = [
    ("Dashboard", ""),
    ("Colleges", ""),
    ("Knowledge Base", ""),
    ("Escalations", ""),
    ("Choice Filling", ""),
    ("Counselor Chat", ""),
]


def _slug(label: str) -> str:
    return label.lower().replace(" ", "-")


def _render_nav(items: list[tuple[str, str]]) -> None:
    current = st.session_state.nav
    for label, icon in items:
        prefix = f"{icon} " if icon else ""
        with st.container(key=f"navitem-{_slug(label)}"):
            if st.button(
                f"{prefix}{label}".strip(), key=f"nav_{label}", use_container_width=True
            ):
                st.session_state.nav = label
                st.session_state.viewing_college_id = None
                st.rerun()

    active_key = f"st-key-navitem-{_slug(current)}"
    st.markdown(
        f"""
        <style>
        .{active_key} button {{
            background: {PRIMARY_BRIGHT} !important;
            color: white !important;
            border-color: {PRIMARY_BRIGHT} !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.18);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        if st.session_state.role == "student":
            name = st.session_state.get("phone", "Student")
            title = "Coligo Student Portal"
        elif st.session_state.role == "college":
            name = st.session_state.college_name or "College"
            title = "Coligo College Portal"
        else:
            name = "Admin"
            title = "Coligo Admin Portal"

        st.markdown(
            f"""
            <div class="coligo-brand">
                <div class="coligo-brand-title">{title}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="coligo-sidebar-user">
                {avatar_html(name)}
                <div>
                    <div class="coligo-sidebar-user-role">Signed in as</div>
                    <div class="coligo-sidebar-user-name">{name}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.role == "student":
            session_key = st.session_state.get("session_key", "whatsapp:demo_student")
            profile = get_student_profile(session_key)
            cutoff_val = profile.calculated_cutoff or st.session_state.get(
                "cutoff", 186.5
            )
            comm_val = profile.community or st.session_state.get("community", "BC")

            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Cutoff", f"{cutoff_val:g}")
                with col_b:
                    st.metric("Quota", comm_val)

                with st.expander("Update Cutoff / Quota"):
                    new_c = st.number_input(
                        "Cutoff Mark",
                        min_value=77.5,
                        max_value=200.0,
                        value=float(cutoff_val),
                        step=0.25,
                        key="sidebar_cutoff_edit",
                    )
                    new_comm = st.selectbox(
                        "Community Quota",
                        options=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"],
                        index=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"].index(
                            comm_val
                        )
                        if comm_val in ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]
                        else 1,
                        key="sidebar_comm_edit",
                    )
                    if st.button("Save Profile", use_container_width=True):
                        update_student_profile(
                            session_key=session_key,
                            cutoff=new_c,
                            community=new_comm,
                        )
                        st.session_state["cutoff"] = new_c
                        st.session_state["community"] = new_comm
                        st.success("Updated!")
                        st.rerun()

            _render_nav(STUDENT_NAV)
        elif st.session_state.role == "college":
            _render_nav(COLLEGE_NAV)
        else:
            _render_nav(ADMIN_NAV)

        st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("<hr/>", unsafe_allow_html=True)

        if st.session_state.role == "student":
            if st.button(
                "Switch to College / Admin Login",
                key="btn_switch_admin",
                use_container_width=True,
            ):
                log_out()
                st.rerun()
        else:
            if st.button(
                "Switch to Student Portal",
                key="btn_switch_student",
                use_container_width=True,
            ):
                st.session_state["role"] = "student"
                st.session_state["token"] = "student_session_token"
                st.session_state["phone"] = "919999999999 (Demo Student)"
                st.session_state["session_key"] = "whatsapp:demo_student"
                st.session_state["nav"] = "AI Admissions Chatbot"
                st.rerun()

        if st.button("Logout", key="nav_logout", use_container_width=True):
            log_out()
            st.rerun()

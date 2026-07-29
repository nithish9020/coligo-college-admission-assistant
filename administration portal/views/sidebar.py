import streamlit as st

from utils.auth import log_out
from utils.styling import PRIMARY

COLLEGE_NAV = [
    ("Dashboard", "\U0001F3E0"),
    ("College Profile", "\U0001F3EB"),
    ("Courses", "\U0001F4D8"),
    ("Infrastructure", "\U0001F3D7"),
    ("Brochures", "\U0001F4C4"),
]

ADMIN_NAV = [
    ("Dashboard", "\U0001F3E0"),
    ("Colleges", "\U0001F3EB"),
]


def _render_nav(items: list[tuple[str, str]]) -> None:
    current = st.session_state.nav
    for label, icon in items:
        if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
            st.session_state.nav = label
            st.session_state.viewing_college_id = None
            st.rerun()

    active_index = next(
        (i for i, (label, _) in enumerate(items, start=1) if label == current), 1
    )
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] div.stButton:nth-of-type({active_index}) button {{
            background: {PRIMARY} !important;
            color: white !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="coligo-brand">
                <div style="font-size:1.6rem;">\U0001F393</div>
                <div class="coligo-brand-title">Coligo Admin Portal</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.role == "college":
            if st.session_state.college_name:
                st.caption(f"Signed in as **{st.session_state.college_name}**")
            _render_nav(COLLEGE_NAV)
        else:
            st.caption("Signed in as **Platform Admin**")
            _render_nav(ADMIN_NAV)

        st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
        if st.button("\U0001F6AA  Logout", key="nav_logout", use_container_width=True):
            log_out()
            st.rerun()

import streamlit as st
from utils.auth import log_out
from utils.styling import PRIMARY_BRIGHT, avatar_html

COLLEGE_NAV = [
    ("Dashboard", "🏠"),
    ("College Profile", "🏫"),
    ("Courses", "📘"),
    ("Infrastructure", "🏗️"),
    ("Brochures", "📄"),
    ("Choice Filling", "🎯"),
    ("Counselor Chat", "💬"),
]

ADMIN_NAV = [
    ("Dashboard", "🏠"),
    ("Colleges", "🏫"),
    ("Knowledge Base", "📚"),
    ("Escalations", "⚠️"),
    ("Choice Filling", "🎯"),
    ("Counselor Chat", "💬"),
]


def _slug(label: str) -> str:
    return label.lower().replace(" ", "-")


def _render_nav(items: list[tuple[str, str]]) -> None:
    current = st.session_state.nav
    for label, icon in items:
        with st.container(key=f"navitem-{_slug(label)}"):
            if st.button(
                f"{icon}  {label}", key=f"nav_{label}", use_container_width=True
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
        st.markdown(
            """
            <div class="coligo-brand">
                <div style="font-size:1.6rem;">\U0001f393</div>
                <div class="coligo-brand-title">Coligo Admin Portal</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.role == "college":
            name = st.session_state.college_name or "College"
        else:
            name = "Admin"

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

        if st.session_state.role == "college":
            _render_nav(COLLEGE_NAV)
        else:
            _render_nav(ADMIN_NAV)

        st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
        st.markdown("<hr/>", unsafe_allow_html=True)
        if st.button("\U0001f6aa  Logout", key="nav_logout", use_container_width=True):
            log_out()
            st.rerun()

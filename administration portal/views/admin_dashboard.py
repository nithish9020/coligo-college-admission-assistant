import streamlit as st
from utils.api_client import APIError, list_colleges
from utils.styling import badge, render_stat_row


def render_admin_dashboard() -> None:
    try:
        colleges = list_colleges(st.session_state.token)
    except APIError as e:
        st.error(e.message)
        return

    st.title("Admin Dashboard")
    st.caption("Overview across all registered colleges")

    total_courses = sum(c["course_count"] for c in colleges)
    total_brochures = sum(c["brochure_count"] for c in colleges)
    active_colleges = sum(1 for c in colleges if c["is_active"])

    render_stat_row(
        [
            ("Total Colleges", len(colleges)),
            ("Active Colleges", active_colleges),
            ("Total Courses", total_courses),
            ("Total Brochures", total_brochures),
        ]
    )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    st.markdown("#### Recent Colleges")

    recent = sorted(colleges, key=lambda c: c["created_at"], reverse=True)[:5]
    if not recent:
        st.info("No colleges have registered yet.")
    else:
        header = st.columns([2.5, 2, 1, 1, 1, 1])
        for col, label in zip(
            header,
            [
                "College Name",
                "Contact Person",
                "Courses",
                "Brochures",
                "Status",
                "Action",
            ],
            strict=False,
        ):
            col.markdown(f"**{label}**")
        for c in recent:
            row = st.columns([2.5, 2, 1, 1, 1, 1])
            row[0].write(c["college_name"])
            row[1].write(c.get("contact_person") or "-")
            row[2].write(c["course_count"])
            row[3].write(c["brochure_count"])
            row[4].markdown(
                badge("Active" if c["is_active"] else "Inactive"),
                unsafe_allow_html=True,
            )
            if row[5].button("View", key=f"dash_view_{c['id']}"):
                st.session_state.nav = "Colleges"
                st.session_state.viewing_college_id = c["id"]
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

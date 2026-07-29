import streamlit as st

from utils.api_client import (
    APIError,
    download_brochure,
    get_college_detail,
    list_brochures,
    list_colleges,
    list_courses,
    list_facilities,
)
from utils.styling import badge


def _render_college_list() -> None:
    st.title("Colleges")
    st.caption("All colleges registered on the platform")

    try:
        colleges = list_colleges(st.session_state.token)
    except APIError as e:
        st.error(e.message)
        return

    if not colleges:
        st.info("No colleges have registered yet.")
        return

    search = st.text_input("\U0001F50D Search colleges...", placeholder="Search by name")
    if search:
        colleges = [
            c for c in colleges if search.lower() in c["college_name"].lower()
        ]

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    header = st.columns([2.5, 2.5, 1, 1, 1, 1])
    for col, label in zip(
        header,
        ["College Name", "Contact Email", "Courses", "Brochures", "Status", "Action"],
        strict=False,
    ):
        col.markdown(f"**{label}**")
    for c in colleges:
        row = st.columns([2.5, 2.5, 1, 1, 1, 1])
        row[0].write(c["college_name"])
        row[1].write(c["email"])
        row[2].write(c["course_count"])
        row[3].write(c["brochure_count"])
        row[4].markdown(
            badge("Active" if c["is_active"] else "Inactive"), unsafe_allow_html=True
        )
        if row[5].button("View", key=f"college_view_{c['id']}"):
            st.session_state.viewing_college_id = c["id"]
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_college_detail(college_id: int) -> None:
    token = st.session_state.token

    if st.button("← Back to Colleges"):
        st.session_state.viewing_college_id = None
        st.rerun()

    try:
        detail = get_college_detail(token, college_id)
    except APIError as e:
        st.error(e.message)
        return

    st.title(detail["college_name"])
    st.markdown(
        badge("Active" if detail["is_active"] else "Inactive"), unsafe_allow_html=True
    )

    tabs = st.tabs(["Overview", f"Courses ({detail['course_count']})",
                     f"Brochures ({detail['brochure_count']})",
                     f"Facilities ({detail['facility_count']})"])

    with tabs[0]:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**College Type**")
            st.write(detail.get("college_type") or "-")
            st.markdown("**Established Year**")
            st.write(detail.get("established_year") or "-")
            st.markdown("**Affiliated University**")
            st.write(detail.get("affiliated_university") or "-")
            st.markdown("**Contact Person**")
            st.write(detail.get("contact_person") or "-")
            st.markdown("**Contact Email**")
            st.write(detail.get("contact_email") or detail["email"])
            st.markdown("**Contact Phone**")
            st.write(detail.get("contact_phone") or "-")
        with col2:
            st.markdown("**Address**")
            address_parts = [
                detail.get("address"), detail.get("city"),
                detail.get("state"), detail.get("pincode"),
            ]
            st.write(", ".join(p for p in address_parts if p) or "-")
            st.markdown("**Accreditation**")
            st.write(detail.get("accreditation") or "-")
            st.markdown("**Website**")
            st.write(detail.get("website") or "-")
        st.markdown("**About**")
        st.write(detail.get("about") or "No description provided.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        try:
            courses = list_courses(token, college_id=college_id)
        except APIError as e:
            st.error(e.message)
            courses = []
        if not courses:
            st.info("No courses added by this college yet.")
        else:
            st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
            header = st.columns([3, 1, 1.2, 1, 1.3])
            for col, label in zip(
                header,
                ["Course Name", "Program", "Duration", "Intake", "Status"],
                strict=False,
            ):
                col.markdown(f"**{label}**")
            for course in courses:
                row = st.columns([3, 1, 1.2, 1, 1.3])
                row[0].write(course["course_name"])
                row[1].write(course["program_level"])
                row[2].write(course.get("duration") or "-")
                row[3].write(course.get("intake_capacity") or "-")
                row[4].markdown(
                    badge(course["status"].capitalize()), unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        try:
            brochures = list_brochures(token, college_id=college_id)
        except APIError as e:
            st.error(e.message)
            brochures = []
        if not brochures:
            st.info("No brochures uploaded by this college yet.")
        else:
            st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
            header = st.columns([3, 1.5, 1, 1.5, 1])
            for col, label in zip(
                header,
                ["Brochure Title", "Category", "Size", "Uploaded On", "Action"],
                strict=False,
            ):
                col.markdown(f"**{label}**")
            for b in brochures:
                row = st.columns([3, 1.5, 1, 1.5, 1])
                row[0].write(b["title"])
                row[1].write(b.get("category") or "-")
                row[2].write(f"{round(b['file_size_bytes'] / (1024 * 1024), 2)} MB")
                row[3].write(b["uploaded_at"][:10])
                with row[4]:
                    try:
                        pdf_bytes = download_brochure(token, b["id"])
                        st.download_button(
                            "\U0001F441️",
                            data=pdf_bytes,
                            file_name=f"{b['title']}.pdf",
                            mime="application/pdf",
                            key=f"admin_dl_bro_{b['id']}",
                        )
                    except APIError:
                        st.caption("N/A")
            st.markdown("</div>", unsafe_allow_html=True)

    with tabs[3]:
        try:
            facilities = list_facilities(token, college_id=college_id)
        except APIError as e:
            st.error(e.message)
            facilities = []
        if not facilities:
            st.info("No facilities added by this college yet.")
        else:
            for f in facilities:
                st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
                st.markdown(f"**{f['name']}**")
                if f.get("description"):
                    st.caption(f["description"])
                st.markdown("</div>", unsafe_allow_html=True)


def render_admin_colleges() -> None:
    viewing_id = st.session_state.get("viewing_college_id")
    if viewing_id:
        _render_college_detail(viewing_id)
    else:
        _render_college_list()

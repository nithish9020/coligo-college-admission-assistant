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
from utils.styling import (
    avatar_html,
    badge,
    page_header,
    render_footer,
    row_icon_html,
)


def _render_college_list() -> None:
    page_header("", "Colleges", "All colleges registered on the platform")

    try:
        colleges = list_colleges(st.session_state.token)
    except APIError as e:
        st.error(e.message)
        return

    if not colleges:
        st.info("No colleges have registered yet.")
        render_footer()
        return

    search = st.text_input(
        "Search colleges",
        placeholder="Search by name...",
        label_visibility="collapsed",
    )
    if search:
        colleges = [c for c in colleges if search.lower() in c["college_name"].lower()]

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    header = st.columns([2.5, 2.5, 1, 1, 1, 1])
    for col, label in zip(
        header,
        ["COLLEGE NAME", "CONTACT EMAIL", "COURSES", "BROCHURES", "STATUS", "ACTION"],
        strict=False,
    ):
        col.markdown(f"**{label}**")
    for c in colleges:
        row = st.columns([2.5, 2.5, 1, 1, 1, 1])
        with row[0]:
            college_icon = avatar_html(c["college_name"])
            st.markdown(
                f'<div class="coligo-item-row">'
                f"{college_icon}"
                f'<span class="coligo-item-title">{c["college_name"]}</span></div>',
                unsafe_allow_html=True,
            )
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
    render_footer()


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

    detail_icon = avatar_html(detail["college_name"])
    detail_badge = badge("Active" if detail["is_active"] else "Inactive")
    st.markdown(
        f'<div class="coligo-page-header">'
        f"{detail_icon}"
        f"<div><h1>{detail['college_name']}</h1>"
        f"{detail_badge}</div></div>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(
        [
            "Overview",
            f"Courses ({detail['course_count']})",
            f"Brochures ({detail['brochure_count']})",
            f"Facilities ({detail['facility_count']})",
        ]
    )

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
                detail.get("address"),
                detail.get("city"),
                detail.get("state"),
                detail.get("pincode"),
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
                ["COURSE NAME", "PROGRAM", "DURATION", "INTAKE", "STATUS"],
                strict=False,
            ):
                col.markdown(f"**{label}**")
            for course in courses:
                row = st.columns([3, 1, 1.2, 1, 1.3])
                with row[0]:
                    course_icon = row_icon_html("C", "purple")
                    st.markdown(
                        f'<div class="coligo-item-row">'
                        f"{course_icon}"
                        f'<span class="coligo-item-title">'
                        f"{course['course_name']}</span></div>",
                        unsafe_allow_html=True,
                    )
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
                ["BROCHURE TITLE", "CATEGORY", "SIZE", "UPLOADED ON", "ACTION"],
                strict=False,
            ):
                col.markdown(f"**{label}**")
            for b in brochures:
                row = st.columns([3, 1.5, 1, 1.5, 1])
                with row[0]:
                    brochure_icon = row_icon_html("B", "orange")
                    st.markdown(
                        f'<div class="coligo-item-row">'
                        f"{brochure_icon}"
                        f'<span class="coligo-item-title">{b["title"]}</span></div>',
                        unsafe_allow_html=True,
                    )
                row[1].write(b.get("category") or "-")
                row[2].write(f"{round(b['file_size_bytes'] / (1024 * 1024), 2)} MB")
                row[3].write(b["uploaded_at"][:10])
                with row[4]:
                    try:
                        pdf_bytes = download_brochure(token, b["id"])
                        st.download_button(
                            "Download",
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
                facility_icon = row_icon_html("F", "green")
                st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="coligo-item-row">'
                    f"{facility_icon}"
                    f'<span class="coligo-item-title">{f["name"]}</span></div>',
                    unsafe_allow_html=True,
                )
                if f.get("description"):
                    st.caption(f["description"])
                st.markdown("</div>", unsafe_allow_html=True)

    render_footer()


def render_admin_colleges() -> None:
    viewing_id = st.session_state.get("viewing_college_id")
    if viewing_id:
        _render_college_detail(viewing_id)
    else:
        _render_college_list()

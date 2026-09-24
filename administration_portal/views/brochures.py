from typing import Any

import streamlit as st
from utils.api_client import (
    APIError,
    apply_brochure_extraction,
    delete_brochure,
    download_brochure,
    extract_brochure,
    list_brochures,
    update_brochure,
    upload_brochure,
)
from utils.styling import page_header, render_footer, row_icon_html

CATEGORIES = ["Prospectus", "Course Guide", "Placement Brochure", "Facilities", "Other"]
PROGRAM_LEVELS = ["UG", "PG", "Diploma", "PhD"]


def _extraction_key(brochure_id: int) -> str:
    return f"extraction_{brochure_id}"


def _run_extraction(token: str, brochure_id: int) -> None:
    try:
        st.session_state[_extraction_key(brochure_id)] = extract_brochure(
            token, brochure_id
        )
    except APIError as e:
        st.error(f"AI extraction failed: {e.message}")


def _render_extraction_review(token: str, brochure_id: int, result: dict) -> None:
    profile = result.get("college_profile") or {}
    courses = result.get("courses") or []
    facilities = result.get("facilities") or []

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    st.markdown("#### ✨ AI-suggested details from this brochure")
    st.caption(
        "Nothing is saved until you confirm below. Review each field, uncheck "
        "anything you don't want, then apply."
    )

    with st.form(f"extraction_review_form_{brochure_id}"):
        apply_profile = st.checkbox(
            "Apply these profile updates",
            value=bool(profile),
            key=f"ext_apply_profile_{brochure_id}",
        )
        p1, p2 = st.columns(2)
        with p1:
            college_type = st.text_input(
                "College Type",
                value=profile.get("college_type") or "",
                key=f"ext_type_{brochure_id}",
            )
            affiliated_university = st.text_input(
                "Affiliated University",
                value=profile.get("affiliated_university") or "",
                key=f"ext_affil_{brochure_id}",
            )
            established_year = st.number_input(
                "Established Year",
                min_value=0,
                max_value=2100,
                value=profile.get("established_year") or 0,
                step=1,
                key=f"ext_year_{brochure_id}",
            )
            website = st.text_input(
                "Website",
                value=profile.get("website") or "",
                key=f"ext_website_{brochure_id}",
            )
        with p2:
            contact_person = st.text_input(
                "Contact Person",
                value=profile.get("contact_person") or "",
                key=f"ext_person_{brochure_id}",
            )
            contact_email = st.text_input(
                "Contact Email",
                value=profile.get("contact_email") or "",
                key=f"ext_cemail_{brochure_id}",
            )
            contact_phone = st.text_input(
                "Contact Phone",
                value=profile.get("contact_phone") or "",
                key=f"ext_cphone_{brochure_id}",
            )
            accreditation = st.text_input(
                "Accreditation",
                value=profile.get("accreditation") or "",
                key=f"ext_accred_{brochure_id}",
            )
        address = st.text_area(
            "Address",
            value=profile.get("address") or "",
            key=f"ext_address_{brochure_id}",
        )
        city_col, state_col, pin_col = st.columns(3)
        with city_col:
            city = st.text_input(
                "City", value=profile.get("city") or "", key=f"ext_city_{brochure_id}"
            )
        with state_col:
            state = st.text_input(
                "State",
                value=profile.get("state") or "",
                key=f"ext_state_{brochure_id}",
            )
        with pin_col:
            pincode = st.text_input(
                "Pincode",
                value=profile.get("pincode") or "",
                key=f"ext_pincode_{brochure_id}",
            )
        about = st.text_area(
            "About", value=profile.get("about") or "", key=f"ext_about_{brochure_id}"
        )

        st.markdown("---")
        st.markdown(f"**Courses found ({len(courses)})**")
        course_rows: list[dict[str, Any]] = []
        for i, c in enumerate(courses):
            include = st.checkbox(
                f"Add: {c.get('course_name') or f'Course {i + 1}'}",
                value=True,
                key=f"ext_course_inc_{brochure_id}_{i}",
            )
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                name = st.text_input(
                    "Course Name",
                    value=c.get("course_name") or "",
                    key=f"ext_course_name_{brochure_id}_{i}",
                )
                level_value = (
                    c.get("program_level")
                    if c.get("program_level") in PROGRAM_LEVELS
                    else PROGRAM_LEVELS[0]
                )
                level = st.selectbox(
                    "Program Level",
                    PROGRAM_LEVELS,
                    index=PROGRAM_LEVELS.index(level_value),
                    key=f"ext_course_level_{brochure_id}_{i}",
                )
            with cc2:
                duration = st.text_input(
                    "Duration",
                    value=c.get("duration") or "",
                    key=f"ext_course_dur_{brochure_id}_{i}",
                )
                intake = st.number_input(
                    "Intake Capacity",
                    min_value=0,
                    value=c.get("intake_capacity") or 0,
                    step=1,
                    key=f"ext_course_intake_{brochure_id}_{i}",
                )
            with cc3:
                department = st.text_input(
                    "Department",
                    value=c.get("department") or "",
                    key=f"ext_course_dept_{brochure_id}_{i}",
                )
                fees = st.text_input(
                    "Fees",
                    value=c.get("fees") or "",
                    key=f"ext_course_fees_{brochure_id}_{i}",
                )
            status_options = ["draft", "published"]
            status = st.radio(
                "Course Status",
                status_options,
                index=1,
                horizontal=True,
                format_func=lambda s: s.capitalize(),
                key=f"ext_course_status_{brochure_id}_{i}",
                help="Draft courses aren't shown to students until published.",
            )
            eligibility = st.text_area(
                "Eligibility",
                value=c.get("eligibility") or "",
                key=f"ext_course_elig_{brochure_id}_{i}",
            )
            course_rows.append(
                {
                    "include": include,
                    "payload": {
                        "program_level": level,
                        "course_name": name,
                        "course_code": c.get("course_code") or None,
                        "duration": duration or None,
                        "intake_capacity": int(intake) or None,
                        "department": department or None,
                        "status": status,
                        "eligibility": eligibility or None,
                        "fees": fees or None,
                        "course_details": c.get("course_details") or None,
                        "career_opportunities": c.get("career_opportunities") or None,
                    },
                }
            )
            st.markdown("---")

        st.markdown(f"**Facilities found ({len(facilities)})**")
        facility_rows: list[dict[str, Any]] = []
        for i, f in enumerate(facilities):
            include = st.checkbox(
                f"Add: {f.get('name') or f'Facility {i + 1}'}",
                value=True,
                key=f"ext_facility_inc_{brochure_id}_{i}",
            )
            fc1, fc2 = st.columns([1, 2])
            with fc1:
                name = st.text_input(
                    "Facility Name",
                    value=f.get("name") or "",
                    key=f"ext_facility_name_{brochure_id}_{i}",
                )
            with fc2:
                description = st.text_input(
                    "Description",
                    value=f.get("description") or "",
                    key=f"ext_facility_desc_{brochure_id}_{i}",
                )
            facility_rows.append(
                {
                    "include": include,
                    "payload": {"name": name, "description": description or None},
                }
            )

        apply_col, discard_col = st.columns([1, 1])
        with apply_col:
            submitted = st.form_submit_button(
                "Apply selected details", type="primary", use_container_width=True
            )
        with discard_col:
            discarded = st.form_submit_button(
                "Discard suggestions", use_container_width=True
            )

    if discarded:
        st.session_state.pop(_extraction_key(brochure_id), None)
        st.rerun()

    if submitted:
        payload: dict[str, Any] = {
            "courses": [
                row["payload"]
                for row in course_rows
                if row["include"] and row["payload"]["course_name"]
            ],
            "facilities": [
                row["payload"]
                for row in facility_rows
                if row["include"] and row["payload"]["name"]
            ],
        }
        if apply_profile:
            payload["college_profile"] = {
                "college_type": college_type or None,
                "affiliated_university": affiliated_university or None,
                "established_year": int(established_year) or None,
                "website": website or None,
                "accreditation": accreditation or None,
                "contact_person": contact_person or None,
                "contact_email": contact_email or None,
                "contact_phone": contact_phone or None,
                "address": address or None,
                "city": city or None,
                "state": state or None,
                "pincode": pincode or None,
                "about": about or None,
            }
        try:
            apply_brochure_extraction(token, brochure_id, payload)
            st.session_state.pop(_extraction_key(brochure_id), None)
            st.success(
                "Applied — your college profile, courses and facilities have "
                "been updated."
            )
            st.rerun()
        except APIError as e:
            st.error(e.message)

    st.markdown("</div>", unsafe_allow_html=True)


def render_brochures() -> None:
    token = st.session_state.token

    page_header(
        "\U0001f4c4",
        "Brochures",
        "Upload and manage your college brochures (PDF only)",
        "orange",
    )

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    st.markdown("### 🌐 Web Scraping & Knowledge Base Ingestion")
    st.caption(
        "Scrape college websites, discover sub-pages, and automatically generate vector embeddings for pgvector."
    )
    with st.form("web_scrape_form", clear_on_submit=False):
        sc_col1, sc_col2 = st.columns([2, 1])
        with sc_col1:
            target_url = st.text_input(
                "College Website URL *",
                placeholder="e.g. https://www.psgtech.edu or https://cit.edu.in",
            )
        with sc_col2:
            target_college_name = st.text_input(
                "College Name *", placeholder="e.g. PSG Tech"
            )
        if st.form_submit_button(
            "🚀 Scrape Website & Ingest Knowledge Base", type="primary"
        ):
            if not target_url or not target_college_name:
                st.error("Both Target Website URL and College Name are required.")
            else:
                import requests
                from utils.api_client import API_BASE_URL

                with st.spinner(
                    f"Scraping {target_college_name} sub-pages and vectorizing into database..."
                ):
                    try:
                        res = requests.post(
                            f"{API_BASE_URL}/documents/scrape",
                            json={
                                "urls": [target_url.strip()],
                                "college_name": target_college_name.strip(),
                            },
                            timeout=120,
                        )
                        if res.status_code == 200:
                            data = res.json()
                            st.success(
                                f"🎉 Ingestion Success! Total Chunks: {data.get('total_chunks')} | "
                                f"Inserted Chunks: {data.get('inserted_chunks')} | Document: {data.get('document_ref')}"
                            )
                        else:
                            st.error(f"Scraping failed ({res.status_code}): {res.text}")
                    except Exception as ex:
                        st.error(f"Failed to connect to backend scraper: {str(ex)}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    with st.form("upload_brochure_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            title = st.text_input(
                "Brochure Title *", placeholder="e.g. College Prospectus 2026"
            )
        with col2:
            category = st.selectbox("Category", CATEGORIES)
        pdf_file = st.file_uploader("PDF File *", type=["pdf"])

        if st.form_submit_button("\U0001f4e4 Upload Brochure", type="primary"):
            if not title or pdf_file is None:
                st.error("Title and a PDF file are both required.")
            else:
                try:
                    new_brochure = upload_brochure(
                        token, title, category, pdf_file.name, pdf_file.getvalue()
                    )
                    with st.spinner("Brochure uploaded. Reading it with AI..."):
                        _run_extraction(token, new_brochure["id"])
                    st.rerun()
                except APIError as e:
                    st.error(e.message)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        brochures = list_brochures(token)
    except APIError as e:
        st.error(e.message)
        return

    if not brochures:
        st.info("No brochures uploaded yet.")
        render_footer()
        return

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    header = st.columns([3, 1.5, 1, 1.5, 2.4])
    for col, label in zip(
        header,
        ["BROCHURE TITLE", "CATEGORY", "SIZE", "UPLOADED ON", "ACTION"],
        strict=False,
    ):
        col.markdown(f"**{label}**")

    for b in brochures:
        edit_key = f"editing_brochure_{b['id']}"
        row = st.columns([3, 1.5, 1, 1.5, 2.4])
        if st.session_state.get(edit_key):
            new_title = row[0].text_input(
                "Title",
                value=b["title"],
                key=f"bro_title_{b['id']}",
                label_visibility="collapsed",
            )
            new_cat = row[1].selectbox(
                "Category",
                CATEGORIES,
                index=CATEGORIES.index(b["category"])
                if b.get("category") in CATEGORIES
                else 0,
                key=f"bro_cat_{b['id']}",
                label_visibility="collapsed",
            )
            row[2].write(f"{round(b['file_size_bytes'] / (1024 * 1024), 2)} MB")
            row[3].write(b["uploaded_at"][:10])
            with row[4]:
                s_col, c_col = st.columns(2)
                if s_col.button("Save", key=f"save_bro_{b['id']}"):
                    try:
                        update_brochure(
                            token, b["id"], {"title": new_title, "category": new_cat}
                        )
                        st.session_state[edit_key] = False
                        st.rerun()
                    except APIError as e:
                        st.error(e.message)
                if c_col.button("Cancel", key=f"cancel_bro_{b['id']}"):
                    st.session_state[edit_key] = False
                    st.rerun()
        else:
            with row[0]:
                brochure_icon = row_icon_html("\U0001f4c4", "orange")
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
                dl_col, ai_col, e_col, d_col = st.columns(4)
                with dl_col:
                    try:
                        pdf_bytes = download_brochure(token, b["id"])
                        st.download_button(
                            "\U0001f441️",
                            data=pdf_bytes,
                            file_name=f"{b['title']}.pdf",
                            mime="application/pdf",
                            key=f"dl_bro_{b['id']}",
                        )
                    except APIError:
                        st.caption("N/A")
                if ai_col.button(
                    "✨", key=f"ai_bro_{b['id']}", help="Extract details with AI"
                ):
                    with st.spinner("Reading brochure with AI..."):
                        _run_extraction(token, b["id"])
                    st.rerun()
                if e_col.button("✏️", key=f"edit_bro_{b['id']}"):
                    st.session_state[edit_key] = True
                    st.rerun()
                if d_col.button("\U0001f5d1️", key=f"del_bro_{b['id']}"):
                    try:
                        delete_brochure(token, b["id"])
                        st.session_state.pop(_extraction_key(b["id"]), None)
                        st.rerun()
                    except APIError as e:
                        st.error(e.message)

        extraction = st.session_state.get(_extraction_key(b["id"]))
        if extraction:
            _render_extraction_review(token, b["id"], extraction)

    st.markdown("</div>", unsafe_allow_html=True)
    render_footer()

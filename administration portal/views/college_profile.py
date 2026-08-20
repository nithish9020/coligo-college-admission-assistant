import streamlit as st
from utils.api_client import APIError, get_my_profile, update_my_profile, upload_logo
from utils.styling import page_header, render_footer

COLLEGE_TYPES = ["Private", "Government", "Autonomous", "Deemed University"]


def _text(profile: dict, key: str) -> str:
    return profile.get(key) or ""


def render_college_profile() -> None:
    token = st.session_state.token

    try:
        profile = get_my_profile(token)
    except APIError as e:
        st.error(e.message)
        return

    page_header("", "College Profile", "Complete your college information", "blue")

    tabs = st.tabs(
        ["Basic Information", "Contact Information", "Social Links", "Accreditation"]
    )

    # --- Basic Information -------------------------------------------------
    with tabs[0]:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)

        logo_col, upload_col = st.columns([1, 3])
        with logo_col:
            if profile.get("logo_path"):
                st.markdown("**Logo uploaded**")
            else:
                st.markdown("No logo yet")
        with upload_col:
            logo_file = st.file_uploader(
                "Change Logo", type=["png", "jpg", "jpeg"], key="logo_uploader"
            )
            if logo_file is not None and st.button("Upload Logo"):
                try:
                    upload_logo(
                        token,
                        logo_file.name,
                        logo_file.getvalue(),
                        logo_file.type or "image/png",
                    )
                    st.success("Logo updated.")
                    st.rerun()
                except APIError as e:
                    st.error(e.message)

        with st.form("basic_info_form"):
            college_name = st.text_input(
                "College Name *", value=profile["college_name"]
            )
            col1, col2 = st.columns(2)
            with col1:
                current_type = profile.get("college_type") or COLLEGE_TYPES[0]
                college_type = st.selectbox(
                    "College Type *",
                    COLLEGE_TYPES,
                    index=COLLEGE_TYPES.index(current_type)
                    if current_type in COLLEGE_TYPES
                    else 0,
                )
                affiliated_university = st.text_input(
                    "Affiliated University",
                    value=_text(profile, "affiliated_university"),
                )
            with col2:
                established_year = st.number_input(
                    "Established Year",
                    min_value=1800,
                    max_value=2100,
                    value=profile.get("established_year") or 2000,
                    step=1,
                )
            about = st.text_area(
                "About College *", value=_text(profile, "about"), max_chars=2000
            )

            if st.form_submit_button("Save & Next", type="primary"):
                try:
                    update_my_profile(
                        token,
                        {
                            "college_name": college_name,
                            "college_type": college_type,
                            "affiliated_university": affiliated_university or None,
                            "established_year": int(established_year),
                            "about": about or None,
                        },
                    )
                    st.success("Basic information saved.")
                    st.rerun()
                except APIError as e:
                    st.error(e.message)

        st.markdown("</div>", unsafe_allow_html=True)

    # --- Contact Information ------------------------------------------------
    with tabs[1]:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        with st.form("contact_info_form"):
            contact_person = st.text_input(
                "Contact Person", value=_text(profile, "contact_person")
            )
            col1, col2 = st.columns(2)
            with col1:
                contact_email = st.text_input(
                    "Contact Email", value=_text(profile, "contact_email")
                )
            with col2:
                contact_phone = st.text_input(
                    "Contact Phone", value=_text(profile, "contact_phone")
                )
            address = st.text_area("Address", value=_text(profile, "address"))
            col3, col4, col5 = st.columns(3)
            with col3:
                city = st.text_input("City", value=_text(profile, "city"))
            with col4:
                state = st.text_input("State", value=_text(profile, "state"))
            with col5:
                pincode = st.text_input("Pincode", value=_text(profile, "pincode"))

            if st.form_submit_button("Save", type="primary"):
                try:
                    update_my_profile(
                        token,
                        {
                            "contact_person": contact_person or None,
                            "contact_email": contact_email or None,
                            "contact_phone": contact_phone or None,
                            "address": address or None,
                            "city": city or None,
                            "state": state or None,
                            "pincode": pincode or None,
                        },
                    )
                    st.success("Contact information saved.")
                    st.rerun()
                except APIError as e:
                    st.error(e.message)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- Social Links ---------------------------------------------------------
    with tabs[2]:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        with st.form("social_links_form"):
            website = st.text_input("Website", value=_text(profile, "website"))
            facebook = st.text_input("Facebook", value=_text(profile, "facebook"))
            twitter = st.text_input("Twitter / X", value=_text(profile, "twitter"))
            linkedin = st.text_input("LinkedIn", value=_text(profile, "linkedin"))
            instagram = st.text_input("Instagram", value=_text(profile, "instagram"))

            if st.form_submit_button("Save", type="primary"):
                try:
                    update_my_profile(
                        token,
                        {
                            "website": website or None,
                            "facebook": facebook or None,
                            "twitter": twitter or None,
                            "linkedin": linkedin or None,
                            "instagram": instagram or None,
                        },
                    )
                    st.success("Social links saved.")
                    st.rerun()
                except APIError as e:
                    st.error(e.message)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- Accreditation ----------------------------------------------------
    with tabs[3]:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        with st.form("accreditation_form"):
            accreditation = st.text_area(
                "Accreditation Details",
                value=_text(profile, "accreditation"),
                placeholder="e.g. NAAC A+ Grade, NBA Accredited Programs...",
            )
            if st.form_submit_button("Save", type="primary"):
                try:
                    update_my_profile(token, {"accreditation": accreditation or None})
                    st.success("Accreditation details saved.")
                    st.rerun()
                except APIError as e:
                    st.error(e.message)
        st.markdown("</div>", unsafe_allow_html=True)

    render_footer()

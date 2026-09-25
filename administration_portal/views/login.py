import asyncio
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st
from utils.api_client import APIError, login
from utils.auth import log_in
from utils.styling import image_data_uri

from api.services.otp_service import (
    is_valid_phone,
    normalize_phone,
    send_whatsapp_otp,
    verify_whatsapp_otp,
)
from api.services.student_profile_service import (
    get_student_profile,
    update_student_profile,
)

LOGIN_IMAGE_PATH = Path(__file__).resolve().parent.parent / "image" / "login.jpg"

HERO_HTML = """
<div style="background:linear-gradient(160deg, rgba(26,18,53,0.72) 0%,
            rgba(58,43,122,0.6) 100%), url('{image_url}') center/cover no-repeat;
            border-radius:18px; padding:3rem 2.2rem; height:100%;
            min-height:540px; color:white; display:flex; flex-direction:column;
            justify-content:space-between;">
  <div>
    <div style="font-size:2rem;">🎓</div>
    <h2 style="color:white; margin-top:1rem;">Coligo — TNEA Admissions &amp; College Hub</h2>
    <p style="color:#E7E4F5; font-size:0.95rem; line-height:1.5;">
      <strong>For Students:</strong> Instant cutoff eligibility, AI counseling assistant,
      visual comparative graphs, and choice-sheet generators.<br/><br/>
      <strong>For Colleges:</strong> Manage institution profiles, department cutoffs,
      courses, and official brochures in one place.
    </p>
  </div>
  <div style="color:#C9C4E8; font-size:0.8rem;">
    © 2026 Coligo. All rights reserved.
  </div>
</div>
"""


def render_login() -> None:
    left, right = st.columns([1, 1.1], gap="large")

    with left:
        st.markdown(
            HERO_HTML.format(image_url=image_data_uri(str(LOGIN_IMAGE_PATH))),
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        tab_student, tab_admin = st.tabs(
            ["🎓 Student Portal (WhatsApp OTP)", "🏛️ College & Admin Login"]
        )

        with tab_student:
            st.subheader("Student Sign In")
            st.caption(
                "Enter your WhatsApp number to sync cutoff marks & chat history, or try Demo Mode instantly."
            )

            phone_input = st.text_input(
                "WhatsApp Mobile Number",
                placeholder="e.g. 9876543210 or +91 9876543210",
                key="student_login_phone",
            )

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                send_clicked = st.button(
                    "📲 Send WhatsApp OTP", use_container_width=True
                )
            with c_btn2:
                demo_clicked = st.button(
                    "🚀 Explore Demo Mode", type="primary", use_container_width=True
                )

            if send_clicked:
                if not phone_input or not is_valid_phone(phone_input):
                    st.error("Please enter a valid 10-digit mobile number.")
                else:
                    with st.spinner("Dispatching verification code via WhatsApp..."):
                        success, msg, _ = asyncio.run(send_whatsapp_otp(phone_input))
                        if success:
                            st.session_state["otp_sent_to"] = normalize_phone(
                                phone_input
                            )
                            st.success(msg)
                        else:
                            st.error(msg)

            if st.session_state.get("otp_sent_to"):
                st.divider()
                st.markdown(
                    f"💬 Code sent to WhatsApp: **+{st.session_state['otp_sent_to']}**"
                )
                otp_code = st.text_input(
                    "6-Digit Verification Code",
                    max_chars=6,
                    placeholder="Enter 6-digit code",
                    key="student_otp_code_val",
                )
                if st.button(
                    "✅ Verify & Enter Portal",
                    type="primary",
                    use_container_width=True,
                ):
                    if not otp_code or len(otp_code.strip()) < 4:
                        st.error("Please enter the complete 6-digit code.")
                    else:
                        verified, v_msg = verify_whatsapp_otp(
                            st.session_state["otp_sent_to"], otp_code
                        )
                        if verified:
                            norm_phone = st.session_state["otp_sent_to"]
                            session_key = f"whatsapp:{norm_phone}"
                            st.session_state["token"] = f"student_{norm_phone}"
                            st.session_state["role"] = "student"
                            st.session_state["authenticated"] = True
                            st.session_state["phone"] = norm_phone
                            st.session_state["session_key"] = session_key
                            st.session_state["nav"] = "AI Admissions Chatbot"
                            st.session_state["history_synced"] = False
                            st.session_state.pop("messages", None)

                            profile = get_student_profile(session_key)
                            st.session_state["cutoff"] = (
                                profile.calculated_cutoff or 186.5
                            )
                            st.session_state["community"] = profile.community or "BC"
                            st.session_state["district"] = (
                                profile.preferred_district or "Coimbatore"
                            )
                            st.success("Verification successful! Welcome to Coligo.")
                            st.rerun()
                        else:
                            st.error(v_msg)

            if demo_clicked:
                session_key = "whatsapp:demo_student"
                st.session_state["token"] = "student_demo_token"
                st.session_state["role"] = "student"
                st.session_state["authenticated"] = True
                st.session_state["phone"] = "919999999999 (Demo Student)"
                st.session_state["session_key"] = session_key
                st.session_state["nav"] = "AI Admissions Chatbot"
                st.session_state["history_synced"] = False
                st.session_state.pop("messages", None)

                update_student_profile(
                    session_key=session_key,
                    cutoff=186.5,
                    community="BC",
                    district="Coimbatore",
                )
                st.session_state["cutoff"] = 186.5
                st.session_state["community"] = "BC"
                st.session_state["district"] = "Coimbatore"
                st.rerun()

        with tab_admin:
            st.subheader("College & Admin Login")
            st.caption(
                "Sign in with email to manage college details, courses, and brochures."
            )

            with st.form("login_form", border=False):
                email = st.text_input("Email Address", placeholder="Enter your email")
                password = st.text_input(
                    "Password", type="password", placeholder="Enter your password"
                )
                submitted = st.form_submit_button(
                    "Login", type="primary", use_container_width=True
                )

            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    try:
                        token_response = login(email.strip(), password)
                        log_in(token_response, email=email.strip())
                        st.rerun()
                    except APIError as e:
                        st.error(e.message)

            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            st.caption("New to the platform?")
            if st.button("Register your college", use_container_width=True):
                st.session_state.page = "signup"
                st.rerun()

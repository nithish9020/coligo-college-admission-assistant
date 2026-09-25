"""WhatsApp OTP Authentication Modal & View for Coligo Streamlit Portal."""

import streamlit as st

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


def render_auth_page() -> None:
    """Render full-screen glassmorphic login card with WhatsApp OTP."""
    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #4F46E5; margin-bottom: 4px; font-weight: 800;">
                    Coligo Portal
                </h1>
                <p style="color: #64748B; font-size: 1.05rem;">
                    TNEA Engineering Admission Assistant & Analytics Hub
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("### 🔐 Student WhatsApp Sign In")
            st.markdown(
                "Enter your WhatsApp mobile number to sync your profile, "
                "cutoff marks, and chat history seamlessly."
            )

            phone_input = st.text_input(
                "WhatsApp Mobile Number",
                placeholder="e.g. 98765 43210 or +91 9876543210",
                key="login_phone_input",
            )

            c_btn1, c_btn2 = st.columns([1, 1])
            with c_btn1:
                send_clicked = st.button(
                    "📲 Send WhatsApp OTP", use_container_width=True
                )
            with c_btn2:
                demo_clicked = st.button(
                    "🚀 Explore Demo Mode", use_container_width=True
                )

            if send_clicked:
                if not phone_input or not is_valid_phone(phone_input):
                    st.error("Please enter a valid 10-digit mobile number.")
                else:
                    with st.spinner("Dispatching verification code via WhatsApp..."):
                        import asyncio

                        success, msg, _ = asyncio.run(send_whatsapp_otp(phone_input))
                        if success:
                            st.session_state["otp_sent_to"] = normalize_phone(
                                phone_input
                            )
                            st.success(msg)
                        else:
                            st.error(msg)

            # If OTP has been dispatched, display code entry box
            if st.session_state.get("otp_sent_to"):
                st.divider()
                st.markdown(
                    f"💬 Code sent to WhatsApp: **+{st.session_state['otp_sent_to']}**"
                )
                otp_code = st.text_input(
                    "6-Digit Verification Code",
                    max_chars=6,
                    placeholder="Enter code from WhatsApp",
                    key="login_otp_code",
                )

                if st.button(
                    "✅ Verify & Enter",
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
                            st.session_state["authenticated"] = True
                            st.session_state["phone"] = norm_phone
                            st.session_state["session_key"] = session_key

                            profile = get_student_profile(session_key)
                            st.session_state["cutoff"] = profile.calculated_cutoff
                            st.session_state["community"] = profile.community or "BC"
                            st.session_state["district"] = (
                                profile.preferred_district or "Coimbatore"
                            )

                            st.success("Verification successful! Welcome.")
                            st.rerun()
                        else:
                            st.error(v_msg)

            if demo_clicked:
                session_key = "whatsapp:demo_student"
                st.session_state["authenticated"] = True
                st.session_state["phone"] = "919999999999 (Demo)"
                st.session_state["session_key"] = session_key

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

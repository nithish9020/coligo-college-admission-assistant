import streamlit as st
from utils.api_client import APIError, signup_college
from utils.auth import log_in

HERO_HTML = """
<div style="background:linear-gradient(160deg,#1A1235 0%,#3A2B7A 100%);
            border-radius:18px; padding:3rem 2.2rem; height:100%;
            min-height:520px; color:white; display:flex; flex-direction:column;
            justify-content:space-between;">
  <div>
    <div style="font-size:2rem;">\U0001f393</div>
    <h2 style="color:white; margin-top:1rem;">Register Your College</h2>
    <p style="color:#C9C4E8; font-size:0.95rem; line-height:1.5;">
      Create your college account to manage profile, courses,
      infrastructure and brochures.
    </p>
  </div>
  <div style="color:#9089B8; font-size:0.8rem;">
    © 2026 Coligo. All rights reserved.
  </div>
</div>
"""


def render_signup() -> None:
    left, right = st.columns([1, 1.1], gap="large")

    with left:
        st.markdown(HERO_HTML, unsafe_allow_html=True)

    with right:
        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
        st.subheader("Create College Account")
        st.caption("Only colleges can sign up here.")

        with st.form("signup_form", border=False):
            college_name = st.text_input(
                "College Name", placeholder="e.g. Springfield Engineering College"
            )
            email = st.text_input("Email Address", placeholder="Enter your email")
            password = st.text_input(
                "Password", type="password", placeholder="Minimum 6 characters"
            )
            confirm_password = st.text_input(
                "Confirm Password", type="password", placeholder="Re-enter password"
            )
            submitted = st.form_submit_button(
                "Create Account", type="primary", use_container_width=True
            )

        if submitted:
            if not college_name or not email or not password:
                st.error("Please fill in all fields.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters long.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    token_response = signup_college(
                        college_name.strip(), email.strip(), password
                    )
                    log_in(token_response)
                    st.success("Account created successfully!")
                    st.rerun()
                except APIError as e:
                    st.error(e.message)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.caption("Already have an account?")
        if st.button("Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

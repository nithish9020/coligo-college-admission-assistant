from pathlib import Path

import streamlit as st
from utils.api_client import APIError, login
from utils.auth import log_in
from utils.styling import image_data_uri

LOGIN_IMAGE_PATH = Path(__file__).resolve().parent.parent / "image" / "login.jpg"

HERO_HTML = """
<div style="background:linear-gradient(160deg, rgba(26,18,53,0.72) 0%,
            rgba(58,43,122,0.6) 100%), url('{image_url}') center/cover no-repeat;
            border-radius:18px; padding:3rem 2.2rem; height:100%;
            min-height:520px; color:white; display:flex; flex-direction:column;
            justify-content:space-between;">
  <div>
    <h2 style="color:white;">College Admission &amp; Course Portal</h2>
    <p style="color:#E7E4F5; font-size:0.95rem; line-height:1.5;">
      Manage your college details, courses and brochures in one place.
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
        st.markdown("<div style='height:2.5rem'></div>", unsafe_allow_html=True)
        st.subheader("Welcome Back!")
        st.caption("Login to continue to your account.")

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

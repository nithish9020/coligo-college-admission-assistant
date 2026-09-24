import streamlit as st
from utils.auth import init_session_state, is_authenticated, restore_session_from_cookie
from utils.styling import inject_base_css
from views.admin_colleges import render_admin_colleges
from views.admin_dashboard import render_admin_dashboard
from views.brochures import render_brochures
from views.chat_simulator import render_chat_simulator
from views.choice_filling import render_choice_filling
from views.college_dashboard import render_college_dashboard
from views.college_profile import render_college_profile
from views.courses import render_courses
from views.escalations import render_escalations
from views.infrastructure import render_infrastructure
from views.knowledge_base import render_knowledge_base
from views.login import render_login
from views.sidebar import render_sidebar
from views.signup import render_signup

init_session_state()
restore_session_from_cookie()

st.set_page_config(
    page_title="Coligo Admin Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded" if is_authenticated() else "collapsed",
)

inject_base_css()

COLLEGE_ROUTES = {
    "Dashboard": render_college_dashboard,
    "College Profile": render_college_profile,
    "Courses": render_courses,
    "Infrastructure": render_infrastructure,
    "Brochures": render_brochures,
    "Choice Filling": render_choice_filling,
    "Counselor Chat": render_chat_simulator,
}

ADMIN_ROUTES = {
    "Dashboard": render_admin_dashboard,
    "Colleges": render_admin_colleges,
    "Knowledge Base": render_knowledge_base,
    "Escalations": render_escalations,
    "Choice Filling": render_choice_filling,
    "Counselor Chat": render_chat_simulator,
}


def main() -> None:
    if not is_authenticated():
        if st.session_state.page == "signup":
            render_signup()
        else:
            render_login()
        return

    render_sidebar()

    if st.session_state.role == "college":
        routes = COLLEGE_ROUTES
    else:
        routes = ADMIN_ROUTES

    view = routes.get(st.session_state.nav, routes["Dashboard"])
    view()


if __name__ == "__main__":
    main()

import sys
from pathlib import Path

# Ensure repo root is top of sys.path so 'api' and 'app' packages resolve correctly
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
_PORTAL_DIR = str(Path(__file__).resolve().parent)
if _PORTAL_DIR in sys.path:
    sys.path.remove(_PORTAL_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
if _PORTAL_DIR not in sys.path:
    sys.path.append(_PORTAL_DIR)

if "app" in sys.modules and not hasattr(sys.modules["app"], "__path__"):
    del sys.modules["app"]

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

from app.components.analytics_view import render_analytics_view
from app.components.chat_view import render_chat_view
from app.components.choice_sheet_view import render_choice_sheet_view
from app.components.compare_view import render_compare_view
from app.components.matrix_view import render_matrix_view
from app.components.placement_view import render_placement_view
from app.components.rank_predictor_view import render_rank_predictor_view
from app.components.upward_simulator_view import render_upward_simulator_view

st.set_page_config(
    page_title="Coligo — TNEA Admissions & College Hub",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
restore_session_from_cookie()

inject_base_css()

STUDENT_ROUTES = {
    "AI Admissions Chatbot": render_chat_view,
    "Cutoff Visualizer & Graphs": render_analytics_view,
    "Head-to-Head College Comparator": render_compare_view,
    "Seat Matrix & Quota Pie Charts": render_matrix_view,
    "Placement & Recruiter Analytics": render_placement_view,
    "3-Tier Choice Sheet Builder": render_choice_sheet_view,
    "TNEA Rank & Round Predictor": render_rank_predictor_view,
    "Upward Movement Simulator": render_upward_simulator_view,
}

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

    if st.session_state.role == "student":
        routes = STUDENT_ROUTES
        view = routes.get(st.session_state.nav, routes["AI Admissions Chatbot"])
    elif st.session_state.role == "college":
        routes = COLLEGE_ROUTES
        view = routes.get(st.session_state.nav, routes["Dashboard"])
    else:
        routes = ADMIN_ROUTES
        view = routes.get(st.session_state.nav, routes["Dashboard"])
    view()


if __name__ == "__main__":
    main()

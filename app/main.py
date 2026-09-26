"""Coligo — TNEA Engineering Admission Assistant & Visual Analytics Portal."""

import streamlit as st

from app.components.analytics_view import render_analytics_view
from app.components.auth_modal import render_auth_page
from app.components.chat_view import render_chat_view
from app.components.choice_sheet_view import render_choice_sheet_view
from app.components.compare_view import render_compare_view
from app.components.matrix_view import render_matrix_view
from app.components.placement_view import render_placement_view
from app.components.rank_predictor_view import render_rank_predictor_view
from app.components.sidebar import render_sidebar
from app.components.upward_simulator_view import render_upward_simulator_view

# Configure page settings
st.set_page_config(
    page_title="Coligo — TNEA Admissions Portal",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom modern CSS styling
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Polished header and banner styles */
h1, h2, h3 {
    letter-spacing: -0.02em;
}

/* Chat bubble styling */
[data-testid="stChatMessage"] {
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 12px;
    border: 1px solid rgba(226, 232, 240, 0.8);
}

/* Metric styling */
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #4F46E5 !important;
}

/* Button styling */
.stButton>button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.15s ease-in-out;
}
.stButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main() -> None:
    """Main application lifecycle controller."""
    # Check if student is authenticated via WhatsApp OTP or Demo mode
    if not st.session_state.get("authenticated", False):
        render_auth_page()
        return

    # Render sidebar and handle navigation
    selected_view = render_sidebar()

    if selected_view == "AI Admissions Chatbot":
        render_chat_view()
    elif selected_view == "Cutoff Visualizer & Graphs":
        render_analytics_view()
    elif selected_view == "Head-to-Head College Comparator":
        render_compare_view()
    elif selected_view == "Seat Matrix & Quota Pie Charts":
        render_matrix_view()
    elif selected_view == "Placement & Recruiter Analytics":
        render_placement_view()
    elif selected_view == "3-Tier Choice Sheet Builder":
        render_choice_sheet_view()
    elif selected_view == "TNEA Rank & Round Predictor":
        render_rank_predictor_view()
    elif selected_view == "Upward Movement Simulator":
        render_upward_simulator_view()


if __name__ == "__main__":
    main()

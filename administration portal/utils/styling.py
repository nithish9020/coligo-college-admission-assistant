"""Custom CSS + small HTML helpers so Streamlit mirrors the purple/white
admin-portal look from the sample UI (dark sidebar, pill badges, cards)."""

import streamlit as st

PRIMARY = "#6C5CE7"
PRIMARY_DARK = "#4C3AA0"
SIDEBAR_BG = "#1A1235"
SIDEBAR_BG_2 = "#241C4A"

BADGE_COLORS = {
    "published": ("#E6F9EE", "#1E9E5A"),
    "active": ("#E6F9EE", "#1E9E5A"),
    "draft": ("#FFF4E5", "#B76E00"),
    "pending": ("#FFF4E5", "#B76E00"),
    "inactive": ("#F1F1F5", "#6B7280"),
    "ug": ("#EEF1FF", "#4C3AA0"),
    "pg": ("#FDEEFB", "#A6329F"),
}


def inject_base_css() -> None:
    st.markdown(
        f"""
        <style>
        #MainMenu, footer {{ visibility: hidden; }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {SIDEBAR_BG} 0%, {SIDEBAR_BG_2} 100%);
        }}
        [data-testid="stSidebar"] * {{ color: #E7E4F5 !important; }}
        [data-testid="stSidebar"] .stButton > button {{
            width: 100%;
            text-align: left;
            background: transparent;
            border: none;
            padding: 0.55rem 0.9rem;
            margin-bottom: 2px;
            border-radius: 8px;
            font-size: 0.95rem;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(255,255,255,0.08);
        }}
        [data-testid="stSidebar"] .nav-active button {{
            background: {PRIMARY} !important;
            color: white !important;
        }}

        .coligo-card {{
            background: #FFFFFF;
            border: 1px solid #ECEBF3;
            border-radius: 14px;
            padding: 1.25rem 1.4rem;
            box-shadow: 0 1px 3px rgba(20, 16, 60, 0.04);
            margin-bottom: 1rem;
        }}

        .coligo-badge {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
        }}

        .coligo-stat-value {{ font-size: 1.9rem; font-weight: 700; color: #1F2430; }}
        .coligo-stat-label {{ font-size: 0.85rem; color: #8A8CA5; }}

        div.stButton > button[kind="primary"] {{
            background: {PRIMARY};
            border: none;
        }}
        div.stButton > button[kind="primary"]:hover {{ background: {PRIMARY_DARK}; }}

        .coligo-brand {{
            display: flex; align-items: center; gap: 10px;
            padding: 0.5rem 0.2rem 1.2rem 0.2rem;
        }}
        .coligo-brand-title {{ font-weight: 700; font-size: 1.05rem; color: white; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str | None = None) -> str:
    key = (kind or text or "").strip().lower()
    bg, fg = BADGE_COLORS.get(key, ("#EEF1FF", PRIMARY_DARK))
    return (
        f'<span class="coligo-badge" style="background:{bg};color:{fg};">{text}</span>'
    )


def stat_card(label: str, value) -> str:
    return (
        '<div class="coligo-card">'
        f'<div class="coligo-stat-value">{value}</div>'
        f'<div class="coligo-stat-label">{label}</div>'
        "</div>"
    )


def render_stat_row(items: list[tuple[str, object]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items, strict=False):
        with col:
            st.markdown(stat_card(label, value), unsafe_allow_html=True)

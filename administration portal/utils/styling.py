"""Custom CSS + small HTML component helpers giving the Streamlit admin
portal a polished dashboard look (indigo sidebar, icon-chip stat cards,
pill badges, clickable action rows) matching the product's design reference.

Explicit color rules are used everywhere on purpose: Streamlit's own
light/dark auto-detection otherwise fights our custom backgrounds and
produces washed-out, low-contrast text.
"""

import base64
import functools
from pathlib import Path

import streamlit as st

# --- Palette -----------------------------------------------------------
PRIMARY = "#6C5CE7"
PRIMARY_BRIGHT = "#7C5CFC"
PRIMARY_DARK = "#4C3AA0"
PRIMARY_TINT = "#EFECFE"

SIDEBAR_FROM = "#181246"
SIDEBAR_TO = "#241C55"
SIDEBAR_TEXT = "#C9C4E8"
SIDEBAR_TEXT_MUTED = "#8A82B8"

INK = "#101828"  # headings
BODY = "#344054"  # body text
MUTED = "#667085"  # captions / labels
SURFACE = "#FFFFFF"
PAGE_BG = "#F6F5FC"
BORDER = "#ECEAF6"

# Rotating accent used for icon chips / stat cards, in reference order.
ACCENTS = {
    "purple": ("#F0ECFE", PRIMARY),
    "blue": ("#E7F1FF", "#2F6FED"),
    "green": ("#E7F9EF", "#12925B"),
    "orange": ("#FFF1E3", "#B5610C"),
    "gray": ("#F2F4F7", "#475467"),
}
ACCENT_CYCLE = ["purple", "blue", "green", "orange"]

BADGE_COLORS = {
    "published": ("#ECFDF3", "#027A48"),
    "active": ("#ECFDF3", "#027A48"),
    "draft": ("#FFFAEB", "#B54708"),
    "pending": ("#FFFAEB", "#B54708"),
    "inactive": ("#F2F4F7", "#475467"),
    "ug": (PRIMARY_TINT, PRIMARY_DARK),
    "pg": ("#FDEEFB", "#A6329F"),
}

FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?"
    "family=Sora:wght@600;700;800&family=Manrope:wght@400;500;600;700&display=swap"
)


@functools.lru_cache(maxsize=None)
def image_data_uri(path: str) -> str:
    """Base64-encode a local image so it can be used in CSS `url()`."""
    data = Path(path).read_bytes()
    suffix = Path(path).suffix.lstrip(".").lower()
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"


def inject_base_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('{FONT_IMPORT}');

        :root {{ color-scheme: light; }}

        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}

        html, body, [data-testid="stAppViewContainer"], .main {{
            background: {PAGE_BG} !important;
            font-family: 'Manrope', -apple-system, sans-serif;
            color: {BODY} !important;
        }}

        /* --- Force readable text everywhere in the main content area --- */
        [data-testid="stAppViewContainer"] p,
        [data-testid="stAppViewContainer"] span,
        [data-testid="stAppViewContainer"] label,
        [data-testid="stAppViewContainer"] li,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] * {{
            color: {BODY} !important;
        }}
        [data-testid="stAppViewContainer"] h1,
        [data-testid="stAppViewContainer"] h2,
        [data-testid="stAppViewContainer"] h3,
        [data-testid="stAppViewContainer"] h4 {{
            color: {INK} !important;
            font-family: 'Sora', 'Manrope', sans-serif !important;
            font-weight: 700 !important;
            text-wrap: balance;
        }}
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{
            color: {MUTED} !important;
        }}
        [data-testid="stAppViewContainer"] .coligo-card strong {{
            display: block;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: {MUTED} !important;
        }}

        /* Inputs / widgets */
        [data-testid="stAppViewContainer"] input,
        [data-testid="stAppViewContainer"] textarea,
        [data-testid="stAppViewContainer"] select {{
            color: {INK} !important;
            background: {SURFACE} !important;
        }}
        [data-testid="stTextInput"] > div > div,
        [data-testid="stTextArea"] > div,
        [data-testid="stNumberInput"] > div > div,
        [data-baseweb="select"] > div {{
            border-radius: 10px !important;
            border-color: {BORDER} !important;
        }}

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {{
            background: linear-gradient(190deg, {SIDEBAR_FROM} 0%, {SIDEBAR_TO} 100%);
            padding-top: 0.5rem;
        }}
        [data-testid="stSidebar"] * {{ color: {SIDEBAR_TEXT} !important; }}
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{
            color: {SIDEBAR_TEXT_MUTED} !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            width: 100%;
            text-align: left;
            background: transparent;
            border: 1px solid transparent;
            padding: 0.6rem 1rem;
            margin-bottom: 4px;
            border-radius: 10px;
            font-family: 'Manrope', sans-serif;
            font-weight: 600;
            font-size: 0.92rem;
            transition: background 0.15s ease;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(255,255,255,0.08);
            border-color: rgba(255,255,255,0.08);
        }}
        [data-testid="stSidebar"] .stButton > button:focus:not(:active) {{
            box-shadow: none;
        }}
        [data-testid="stSidebar"] hr {{
            border-color: rgba(255,255,255,0.12);
        }}

        .coligo-brand {{
            display: flex; align-items: center; gap: 10px;
            padding: 0.6rem 0.2rem 1rem 0.2rem;
        }}
        .coligo-brand-title {{
            font-family: 'Sora', sans-serif;
            font-weight: 700; font-size: 1.05rem; color: white !important;
        }}

        .coligo-sidebar-user {{
            display: flex; align-items: center; gap: 10px;
            padding: 0.5rem 0.4rem 1.1rem 0.4rem;
            margin-bottom: 0.4rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .coligo-avatar {{
            flex-shrink: 0;
            width: 36px; height: 36px; border-radius: 50%;
            background: {PRIMARY_BRIGHT};
            color: white !important;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Sora', sans-serif; font-weight: 700; font-size: 0.95rem;
        }}
        .coligo-sidebar-user-name {{ font-weight: 700; color: white !important; font-size: 0.92rem; }}
        .coligo-sidebar-user-role {{ font-size: 0.76rem; color: {SIDEBAR_TEXT_MUTED} !important; }}

        /* --- Page header (icon chip + title + subtitle) --- */
        .coligo-page-header {{
            display: flex; align-items: center; gap: 14px;
            margin-bottom: 1.4rem;
        }}
        .coligo-page-header .coligo-icon-chip {{ width: 52px; height: 52px; font-size: 1.5rem; }}
        .coligo-page-header h1 {{
            font-size: 1.7rem !important; margin: 0 !important; line-height: 1.2 !important;
        }}
        .coligo-page-header .coligo-page-subtitle {{
            color: {MUTED} !important; font-size: 0.92rem; margin-top: 2px;
        }}

        /* --- Icon chips --- */
        .coligo-icon-chip {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 40px; height: 40px; border-radius: 12px;
            font-size: 1.15rem; flex-shrink: 0;
        }}

        /* --- Cards / surfaces --- */
        .coligo-card {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 1.4rem 1.5rem;
            box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 1px 3px rgba(16,24,40,0.05);
            margin-bottom: 1.1rem;
        }}
        .coligo-card-header {{
            display: flex; align-items: center; gap: 10px;
            font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.02rem;
            color: {INK} !important; margin-bottom: 1rem;
        }}
        .coligo-item-row {{
            display: flex; align-items: center; gap: 12px;
        }}
        .coligo-item-title {{
            font-weight: 700; font-size: 0.95rem; color: {INK} !important;
        }}

        /* --- Stat cards --- */
        .coligo-stat-card {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 1px 2px rgba(16,24,40,0.04);
            margin-bottom: 1.1rem;
        }}
        .coligo-stat-card .coligo-icon-chip {{ margin-bottom: 0.7rem; }}
        .coligo-stat-value {{
            font-family: 'Sora', sans-serif;
            font-size: 1.6rem; font-weight: 700; color: {INK} !important;
            font-variant-numeric: tabular-nums; line-height: 1.25;
        }}
        .coligo-stat-label {{
            font-size: 0.86rem; font-weight: 700; color: {INK} !important;
        }}
        .coligo-stat-sublabel {{
            font-size: 0.78rem; color: {MUTED} !important; margin-top: 1px;
        }}

        .coligo-badge {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.01em;
        }}

        /* --- Empty state --- */
        .coligo-empty-state {{
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; gap: 0.9rem; padding: 2.2rem 1rem;
            text-align: center;
        }}
        .coligo-empty-circle {{
            width: 76px; height: 76px; border-radius: 50%;
            border: 2px dashed {BORDER};
            display: flex; align-items: center; justify-content: center;
            font-size: 1.8rem; background: {PAGE_BG};
        }}
        .coligo-empty-title {{ font-weight: 700; color: {INK} !important; }}
        .coligo-empty-subtitle {{ font-size: 0.85rem; color: {MUTED} !important; }}

        /* --- Action rows (clickable via invisible overlay button) --- */
        .coligo-action-row {{
            position: relative;
            display: flex; align-items: center; gap: 12px;
            padding: 0.75rem 0.6rem; border-radius: 12px;
            transition: background 0.15s ease;
        }}
        .coligo-action-row:hover {{ background: {PAGE_BG}; }}
        .coligo-action-title {{ font-weight: 700; color: {INK} !important; font-size: 0.92rem; }}
        .coligo-action-subtitle {{ font-size: 0.8rem; color: {MUTED} !important; }}
        .coligo-action-chevron {{ margin-left: auto; color: {MUTED} !important; font-size: 1.1rem; }}
        div[class*="st-key-action-"] {{ position: relative; margin-bottom: 2px; }}
        div[class*="st-key-action-"] div[data-testid="stVerticalBlock"] > div:has(.stButton) {{
            position: absolute; inset: 0;
        }}
        div[class*="st-key-action-"] .stButton button {{
            width: 100%; height: 100%;
            opacity: 0; cursor: pointer;
        }}

        /* --- Row icon chips (small, inline before text) --- */
        .coligo-row-icon {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 30px; height: 30px; border-radius: 8px; font-size: 0.9rem;
        }}

        /* --- Value pills (non-status colored pills for numbers/durations) --- */
        .coligo-pill {{
            display: inline-block; padding: 2px 10px; border-radius: 8px;
            font-size: 0.8rem; font-weight: 700;
        }}

        /* --- Footer --- */
        .coligo-footer {{
            text-align: center; color: {MUTED} !important;
            font-size: 0.8rem; padding: 2rem 0 1rem 0;
        }}

        /* --- Buttons --- */
        div.stButton > button {{
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid {BORDER};
        }}
        div.stButton > button[kind="primary"] {{
            background: {PRIMARY_BRIGHT};
            border: none;
            box-shadow: 0 1px 2px rgba(108,92,231,0.28);
        }}
        div.stButton > button[kind="primary"]:hover {{ background: {PRIMARY_DARK}; }}
        div.stButton > button[kind="secondary"] {{
            background: {SURFACE};
            color: {BODY} !important;
        }}
        div.stButton > button[kind="secondary"]:hover {{
            border-color: {PRIMARY};
            color: {PRIMARY} !important;
        }}

        [data-testid="stForm"] {{
            border: none;
            padding: 0;
        }}

        [data-testid="stTabs"] button[role="tab"] {{
            font-weight: 600;
            color: {MUTED} !important;
        }}
        [data-testid="stTabs"] button[aria-selected="true"] {{
            color: {PRIMARY} !important;
        }}
        [data-baseweb="tab-highlight"] {{ background-color: {PRIMARY} !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str | None = None) -> str:
    key = (kind or text or "").strip().lower()
    bg, fg = BADGE_COLORS.get(key, (PRIMARY_TINT, PRIMARY_DARK))
    return (
        f'<span class="coligo-badge" style="background:{bg};color:{fg};">{text}</span>'
    )


def pill(text: str, accent: str = "blue") -> str:
    bg, fg = ACCENTS.get(accent, ACCENTS["blue"])
    return f'<span class="coligo-pill" style="background:{bg};color:{fg};">{text}</span>'


def icon_chip_html(icon: str, accent: str = "purple", size: str = "") -> str:
    bg, fg = ACCENTS.get(accent, ACCENTS["purple"])
    style_extra = f' style="width:{size};height:{size};"' if size else ""
    return (
        f'<div class="coligo-icon-chip"{style_extra} '
        f'style="background:{bg};color:{fg};">{icon}</div>'
    )


def row_icon_html(icon: str, accent: str = "purple") -> str:
    bg, fg = ACCENTS.get(accent, ACCENTS["purple"])
    return f'<div class="coligo-row-icon" style="background:{bg};color:{fg};">{icon}</div>'


def avatar_html(name: str) -> str:
    initial = (name or "?").strip()[:1].upper()
    return f'<div class="coligo-avatar">{initial}</div>'


def page_header(icon: str, title: str, subtitle: str, accent: str = "purple") -> None:
    bg, fg = ACCENTS.get(accent, ACCENTS["purple"])
    st.markdown(
        f"""
        <div class="coligo-page-header">
            <div class="coligo-icon-chip" style="background:{bg};color:{fg};">{icon}</div>
            <div>
                <h1>{title}</h1>
                <div class="coligo-page-subtitle">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value, icon: str = "", accent: str = "purple", sublabel: str = "") -> str:
    icon_html = icon_chip_html(icon, accent) if icon else ""
    sub_html = f'<div class="coligo-stat-sublabel">{sublabel}</div>' if sublabel else ""
    return (
        '<div class="coligo-stat-card">'
        f"{icon_html}"
        f'<div class="coligo-stat-value">{value}</div>'
        f'<div class="coligo-stat-label">{label}</div>'
        f"{sub_html}"
        "</div>"
    )


def render_stat_row(items: list[tuple[str, object, str, str]]) -> None:
    """items: list of (label, value, icon, sublabel) tuples. Accent color
    rotates automatically through the reference purple/blue/green/orange
    sequence."""
    cols = st.columns(len(items))
    for i, (col, item) in enumerate(zip(cols, items, strict=False)):
        label, value, icon, sublabel = item
        accent = ACCENT_CYCLE[i % len(ACCENT_CYCLE)]
        with col:
            st.markdown(
                stat_card(label, value, icon, accent, sublabel), unsafe_allow_html=True
            )


def empty_state(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="coligo-empty-state">
            <div class="coligo-empty-circle">{icon}</div>
            <div class="coligo-empty-title">{title}</div>
            <div class="coligo-empty-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def action_row(
    key: str, icon: str, title: str, subtitle: str, accent: str = "purple"
) -> bool:
    """Renders a styled icon-chip + title/subtitle + chevron row that is
    fully clickable (via an invisible button overlaid on top via CSS).
    Returns True on the run where it was clicked."""
    with st.container(key=f"action-{key}"):
        st.markdown(
            f"""
            <div class="coligo-action-row">
                {icon_chip_html(icon, accent)}
                <div>
                    <div class="coligo-action-title">{title}</div>
                    <div class="coligo-action-subtitle">{subtitle}</div>
                </div>
                <div class="coligo-action-chevron">&rsaquo;</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return st.button("", key=f"action_btn_{key}")


def render_footer(brand: str = "Coligo Admin Portal") -> None:
    st.markdown(
        f'<div class="coligo-footer">© 2025 {brand}. All rights reserved.</div>',
        unsafe_allow_html=True,
    )

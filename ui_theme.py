"""Shared Streamlit layout and styling."""

from __future__ import annotations

from typing import List

import streamlit as st
import streamlit.components.v1 as components

__all__ = [
    "inject_global_styles",
    "render_hero",
    "render_kpi",
    "render_panel",
    "close_panel",
    "render_steps",
]

APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Remove Streamlit top chrome (Deploy bar, menu, decoration) */
.stApp > header,
header[data-testid="stHeader"],
[data-testid="stDecoration"],
[data-testid="stToolbar"],
[data-testid="stToolbarActions"],
[data-testid="stHeaderActionElements"],
[data-testid="stMainMenu"],
[data-testid="stAppDeployButton"],
.stDeployButton,
#MainMenu,
button[kind="header"],
button[kind="headerNoPadding"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    opacity: 0 !important;
    overflow: hidden !important;
    pointer-events: none !important;
}

.stApp {
    background: #eef3f9;
}

section.main .block-container {
    padding-top: 0.5rem;
    padding-bottom: 2rem;
    max-width: 1200px;
    background: transparent;
}

/* Prevent empty white cards from CSS-injection markdown wrappers */
[data-testid="stMarkdownContainer"],
[data-testid="stElementContainer"],
.stMarkdown {
    background: transparent !important;
}

iframe[title="streamlit_components_v1.components.html"] {
    display: none !important;
    height: 0 !important;
    border: none !important;
}

.clu-hero {
    background: linear-gradient(125deg, #0f2744 0%, #1e4a7a 45%, #2d6ba8 100%);
    padding: 2.25rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1rem;
    color: #ffffff;
    box-shadow: 0 12px 40px rgba(15, 39, 68, 0.25);
    position: relative;
    overflow: hidden;
}
.clu-hero::after {
    content: '';
    position: absolute;
    right: -40px;
    top: -40px;
    width: 200px;
    height: 200px;
    background: rgba(255,255,255,0.08);
    border-radius: 50%;
}
.clu-hero h1 {
    color: #ffffff !important;
    margin: 0;
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
}
.clu-hero p {
    color: #c5d9f0;
    margin: 0.65rem 0 0 0;
    font-size: 1.05rem;
    max-width: 640px;
}
.clu-badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    color: #e8f4ff;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.clu-panel {
    background: #ffffff;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    border: 1px solid #e8eef4;
    box-shadow: 0 2px 12px rgba(15, 39, 68, 0.05);
    margin-bottom: 1rem;
}
.clu-panel-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1e3a5f;
    margin-bottom: 0.75rem;
}

.clu-kpi-card {
    background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
    padding: 1.1rem 1.25rem;
    border-radius: 12px;
    border: 1px solid #e8eef4;
    box-shadow: 0 4px 16px rgba(15, 39, 68, 0.06);
    height: 100%;
}
.clu-kpi-label {
    font-size: 0.72rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
}
.clu-kpi-value {
    font-size: 1.85rem;
    font-weight: 700;
    color: #0f2744;
    margin-top: 0.25rem;
}

.clu-step {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    font-size: 0.85rem;
    color: #475569;
    margin-bottom: 0.5rem;
}
.clu-step-num {
    background: #1e4a7a;
    color: white;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 700;
}

div[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f2744 0%, #1a3555 100%);
}
div[data-testid="stSidebar"] * {
    color: #e8f0fa !important;
}
div[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    color: white !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: #eef3f9;
    padding: 0.35rem;
    border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight: 600;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1e4a7a, #2d6ba8);
    border: none;
    font-weight: 600;
    border-radius: 10px;
    padding: 0.5rem 1.25rem;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2d6ba8, #3d7ab8);
}
"""

LOGIN_PAGE_CSS = """
section[data-testid="stSidebar"] {
    display: none !important;
}
section[data-testid="stSidebar"] ~ section.main {
    margin-left: 0 !important;
    width: 100% !important;
}
section.main .block-container {
    max-width: 520px;
    margin: 0 auto;
}
"""


def inject_global_styles(login_page: bool = False) -> None:
    css = APP_CSS + (LOGIN_PAGE_CSS if login_page else "")
    if hasattr(st, "html"):
        st.html(f"<style>{css}</style>", unsafe_allow_javascript=False)
    else:
        components.html(f"<style>{css}</style>", height=0, scrolling=False)


def render_hero(title: str, subtitle: str, badge: str = "CLU Cloud") -> None:
    st.markdown(
        f'<div class="clu-hero">'
        f'<span class="clu-badge">{badge}</span>'
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def render_kpi(label: str, value: str) -> None:
    st.markdown(
        f'<div class="clu-kpi-card">'
        f'<div class="clu-kpi-label">{label}</div>'
        f'<div class="clu-kpi-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def render_panel(title: str) -> None:
    st.markdown(
        f'<div class="clu-panel"><div class="clu-panel-title">{title}</div>',
        unsafe_allow_html=True,
    )


def close_panel() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_steps(steps: List[str]) -> None:
    html_parts = ['<div class="clu-panel">']
    for i, step in enumerate(steps, 1):
        html_parts.append(
            f'<div class="clu-step"><span class="clu-step-num">{i}</span>{step}</div>'
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

"""Shared executive page layout elements."""

from __future__ import annotations

from html import escape

import streamlit as st

from utils.constants import SCOPE_BADGE, SCOPE_LABEL
from utils.html import compact_html


def render_page_header(
    title: str,
    description: str,
    eyebrow: str = "Reddit Lounge Intelligence",
    show_scope: bool = True,
    compact: bool = False,
) -> None:
    """Render the consistent top-of-page executive header."""
    scope = ""
    if show_scope:
        scope = f"""
        <div class="scope-stack">
            <span class="scope-pill">{escape(SCOPE_BADGE)}</span>
            <div class="scope-dates">{escape(SCOPE_LABEL)}</div>
        </div>
        """
    st.markdown(
        compact_html(
            f"""
        <header class="page-hero{' compact' if compact else ''}">
            <div>
                <div class="eyebrow">{escape(eyebrow)}</div>
                <h1>{escape(title)}</h1>
                <p>{escape(description)}</p>
            </div>
            {scope}
        </header>
        """
        ),
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, description: str = "") -> None:
    """Render a compact section title and optional explanatory line."""
    paragraph = f"<p>{escape(description)}</p>" if description else ""
    st.markdown(
        compact_html(
            f"""
        <div class="section-heading">
            <div><h2>{escape(title)}</h2>{paragraph}</div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def render_chart_title(title: str) -> None:
    """Render a high-contrast chart heading outside Plotly's drawing area."""
    st.markdown(
        compact_html(f'<div class="chart-title">{escape(title)}</div>'),
        unsafe_allow_html=True,
    )


def render_method_note(text: str) -> None:
    """Render a restrained methodology/caveat callout."""
    st.markdown(f'<div class="method-note">{escape(text)}</div>', unsafe_allow_html=True)

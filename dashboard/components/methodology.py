"""Presentation helpers for the FAQ / Methodology trust layer."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from utils.html import compact_html


def render_faq_cards(items: tuple[tuple[str, str, str], ...]) -> None:
    """Render compact question-led cards with anchors to deeper sections."""
    markup = "".join(
        compact_html(
            f"""
            <article class="method-faq-card">
                <h3>{escape(question)}</h3>
                <p>{escape(answer)}</p>
                <a href="#{escape(anchor)}">Read the detailed explanation ↓</a>
            </article>
            """
        )
        for question, answer, anchor in items
    )
    st.markdown(f'<div class="method-faq-grid">{markup}</div>', unsafe_allow_html=True)


def render_jump_links(items: tuple[tuple[str, str], ...]) -> None:
    """Render a compact native-anchor index for the long methodology page."""
    links = "".join(
        f'<a href="#{escape(anchor)}">{escape(label)}</a>' for label, anchor in items
    )
    st.markdown(
        compact_html(
            f"""
            <nav class="method-jump-nav" aria-label="Jump to section">
                <strong>Jump to section</strong>
                <div>{links}</div>
            </nav>
            """
        ),
        unsafe_allow_html=True,
    )


def render_funnel(counts: dict[str, int]) -> None:
    """Render the seven frozen analysis stages in executive language."""
    stages = (
        (counts["exploded_comments"], "Reddit comments reviewed", "comments"),
        (counts["experience_bearing"], "Contained lounge-experience feedback", "comments"),
        (counts["analysis_window"], "Fell within the Jan–Aug 2026 analysis period", "comments"),
        (counts["usable_comments"], "Had enough usable experience detail", "comments"),
        (counts["known_comments"], "Had supported brand/lounge attribution", "comments"),
        (counts["extracted_observations"], "Experience observations extracted", "observations"),
        (counts["clean_observations"], "Clean observations retained after quality checks", "observations"),
    )
    markup = "".join(
        compact_html(
            f"""
            <div class="method-funnel-stage {kind}">
                <strong>{value:,}</strong><span>{escape(label)}</span>
            </div>
            {'' if index == len(stages) - 1 else '<div class="method-funnel-arrow" aria-hidden="true">↓</div>'}
            """
        )
        for index, (value, label, kind) in enumerate(stages)
    )
    st.markdown(
        compact_html(
            f"""
            <div class="method-funnel">{markup}</div>
            <div class="method-callout warm">
                The final observation count can exceed the number of comments because one Reddit comment can discuss multiple brands, lounges, airports or parts of the lounge experience.
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_info_cards(items: tuple[tuple[str, str], ...], *, css_class: str = "") -> None:
    """Render a reusable grid of short explanatory cards."""
    markup = "".join(
        compact_html(
            f"""
            <article class="method-info-card {escape(css_class)}">
                <h3>{escape(title)}</h3><p>{escape(body)}</p>
            </article>
            """
        )
        for title, body in items
    )
    st.markdown(f'<div class="method-info-grid">{markup}</div>', unsafe_allow_html=True)


def render_theme_cards(items: tuple[tuple[str, str], ...]) -> None:
    """Render the frozen five-theme executive presentation mapping."""
    markup = "".join(
        compact_html(
            f"""
            <article class="method-theme-card">
                <h3>{escape(title)}</h3><p>{escape(body)}</p>
            </article>
            """
        )
        for title, body in items
    )
    st.markdown(f'<div class="method-theme-grid">{markup}</div>', unsafe_allow_html=True)


def render_definition_pair(
    left_title: str,
    left_body: str,
    right_title: str,
    right_body: str,
) -> None:
    """Render two prominent definition cards."""
    st.markdown(
        compact_html(
            f"""
            <div class="method-definition-grid">
                <article><span>COMMENT</span><h3>{escape(left_title)}</h3><p>{escape(left_body)}</p></article>
                <article><span>OBSERVATION</span><h3>{escape(right_title)}</h3><p>{escape(right_body)}</p></article>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_metric_cards(items: tuple[tuple[str, str, str], ...]) -> None:
    """Render small validation or coverage metrics."""
    markup = "".join(
        compact_html(
            f"""
            <article class="method-metric-card">
                <strong>{escape(value)}</strong><span>{escape(label)}</span><small>{escape(note)}</small>
            </article>
            """
        )
        for value, label, note in items
    )
    st.markdown(f'<div class="method-metric-grid">{markup}</div>', unsafe_allow_html=True)


def render_example_card(
    *,
    label: str,
    title: str,
    comment: str,
    explanation: str,
    mappings: tuple[str, ...],
    url: str,
) -> None:
    """Render one frozen real-comment methodology example."""
    mapping_markup = "".join(f"<li>{escape(item)}</li>" for item in mappings)
    st.markdown(
        compact_html(
            f"""
            <article class="method-example-card">
                <span class="method-example-label">{escape(label)}</span>
                <h3>{escape(title)}</h3>
                <blockquote>{escape(comment)}</blockquote>
                <p>{escape(explanation)}</p>
                <ul>{mapping_markup}</ul>
                <a href="{escape(url)}" target="_blank" rel="noopener noreferrer">View Reddit post ↗</a>
            </article>
            """
        ),
        unsafe_allow_html=True,
    )


def render_glossary(items: tuple[tuple[str, str], ...]) -> None:
    """Render compact plain-English glossary cards."""
    markup = "".join(
        compact_html(
            f"""
            <article class="method-glossary-card">
                <h3>{escape(term)}</h3><p>{escape(definition)}</p>
            </article>
            """
        )
        for term, definition in items
    )
    st.markdown(f'<div class="method-glossary-grid">{markup}</div>', unsafe_allow_html=True)


def compact_validation_table(frame: pd.DataFrame) -> None:
    """Display a small responsive validation table without an index."""
    st.dataframe(frame, hide_index=True, width="stretch")

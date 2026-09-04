"""Presentation components for the executive Home / Dashboard Guide page."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from utils.html import compact_html


def render_home_navigation_card(
    *,
    slug: str,
    number: str,
    question: str,
    description: str,
    target: str,
    cta: str,
) -> None:
    """Render one question-led guide card with a native Streamlit page link."""
    with st.container(border=True, key=f"home-nav-{slug}"):
        st.markdown(
            compact_html(
                f"""
                <div class="home-nav-copy">
                    <span class="home-nav-number">{escape(number)}</span>
                    <h3>{escape(question)}</h3>
                    <p>{escape(description)}</p>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
        st.page_link(
            target,
            label=cta,
            icon=":material/arrow_forward:",
            use_container_width=True,
        )


def render_snapshot_cards(items: list[dict[str, str]]) -> None:
    """Render the frozen data-scope snapshot."""
    markup = "".join(
        compact_html(
            f"""
            <article class="home-kpi-card"{f' title="{escape(item["tooltip"])}"' if item.get("tooltip") else ""}>
                <strong>{escape(item['value'])}</strong>
                <span>{escape(item['label'])}</span>
                <p>{escape(item['support'])}</p>
            </article>
            """
        )
        for item in items
    )
    st.markdown(
        f'<div class="home-kpi-grid">{markup}</div>',
        unsafe_allow_html=True,
    )


def render_methodology_funnel(counts: dict[str, int]) -> None:
    """Render the approved seven-stage methodology funnel."""
    stages = [
        (counts["exploded_comments"], "Reddit comments reviewed", "comments"),
        (counts["experience_bearing"], "Contained lounge-experience feedback", "comments"),
        (counts["analysis_window"], "Fell within the Jan–Aug 2026 analysis period", "comments"),
        (counts["usable_comments"], "Had enough usable experience detail", "comments"),
        (counts["known_comments"], "Had supported brand/lounge attribution", "comments"),
        (counts["extracted_observations"], "Experience observations extracted", "observations"),
        (counts["clean_observations"], "Clean observations retained after quality checks", "observations"),
    ]
    markup = "".join(
        compact_html(
            f"""
            <div class="home-funnel-stage {kind}">
                <strong>{value:,}</strong>
                <span>{escape(label)}</span>
            </div>
            {'' if index == len(stages) - 1 else '<div class="home-funnel-arrow" aria-hidden="true">↓</div>'}
            """
        )
        for index, (value, label, kind) in enumerate(stages)
    )
    st.markdown(
        compact_html(
            f"""
            <div class="home-funnel">{markup}</div>
            <div class="home-inline-note">
                The final observation count can exceed the number of comments because one Reddit comment can discuss multiple brands, lounges, airports or parts of the lounge experience.
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_source_ranking(sources: pd.DataFrame) -> None:
    """Render all canonical source communities in descending comment order."""
    ranked = sources.sort_values(["comments", "subreddit"], ascending=[False, True]).copy()
    maximum = max(float(ranked["comments"].max()), 1.0)
    rows = []
    for rank, row in enumerate(ranked.itertuples(index=False), start=1):
        width = max(4.0, float(row.comments) / maximum * 100)
        rows.append(
            compact_html(
                f"""
                <div class="home-source-row">
                    <span class="home-source-rank">{rank:02d}</span>
                    <strong>r/{escape(str(row.subreddit))}</strong>
                    <div class="home-source-track"><i style="width:{width:.1f}%"></i></div>
                    <span class="home-source-count">{int(row.comments):,} comments</span>
                </div>
                """
            )
        )
    st.markdown(
        f'<div class="home-source-ranking">{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def render_aspect_chips(aspects: list[tuple[str, str]]) -> None:
    """Render the 17 approved specific experience areas with definitions on hover."""
    markup = "".join(
        f'<span class="home-aspect-chip" title="{escape(definition)}">{escape(label)}</span>'
        for label, definition in aspects
    )
    st.markdown(f'<div class="home-aspect-grid">{markup}</div>', unsafe_allow_html=True)

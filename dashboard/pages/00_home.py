"""Home — orientation and navigation for the final executive dashboard."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from components.home import (
    render_home_navigation_card,
    render_methodology_funnel,
    render_snapshot_cards,
    render_source_ranking,
)
from components.layout import render_page_header, render_section_heading
from utils.constants import DATA_DIR, ENTITY_SHORT_NAMES, HEADLINE_ISSUERS
from utils.data_loader import load_canonical_dataset, load_csv, load_home_frozen_summaries
from utils.html import compact_html
from utils.validation import DataContractError, require_columns, require_unique


HOME_STYLE_FILE = Path(__file__).resolve().parents[1] / "assets" / "styles" / "home.css"
THEME_SUMMARY_FILE = DATA_DIR / "56_executive_theme_brand_summary.csv"
HOME_STATUS = "HOME_FINAL_FROZEN"

FUNNEL_STAGES = (
    ("exploded_comments", "Exploded Reddit comment units"),
    ("experience_bearing", "Experience-bearing after Stage 1"),
    ("analysis_window", "2026 YTD production scope"),
    ("usable_comments", "Stage 2A-1 usable"),
    ("known_comments", "Known-attribution Stage 2B population"),
    ("extracted_observations", "Stage 2B extracted observations"),
    ("clean_observations", "Final clean observations"),
)

THEME_CARDS = (
    ("General Lounge Experience", "Overall impression of the lounge experience"),
    (
        "Access & Capacity",
        "Crowding · Wait time & queues · Seating · Access · Reservations",
    ),
    (
        "Food & Beverage",
        "Food quality · Food availability · Beverage & bar",
    ),
    ("Service & Upkeep", "Staff & service · Cleanliness"),
    (
        "Space, Amenities & Convenience",
        "Ambience · Amenities · Wi-Fi/workspace · Family/children · Location · Hours · Value",
    ),
)


def _summary_value(frame: pd.DataFrame, metric: str, dataset: str) -> int:
    require_columns(frame, ["metric", "value"], dataset)
    rows = frame.loc[frame["metric"].astype(str).eq(metric), "value"]
    if len(rows) != 1:
        raise DataContractError(f"{dataset} must contain one row for {metric!r}")
    value = pd.to_numeric(rows.iloc[0], errors="coerce")
    if pd.isna(value):
        raise DataContractError(f"{dataset} has a non-numeric value for {metric!r}")
    return int(value)


def _funnel_counts(funnel: pd.DataFrame) -> dict[str, int]:
    require_columns(funnel, ["stage", "count", "definition"], "FAQ_FUNNEL")
    require_unique(funnel, ["stage"], "FAQ_FUNNEL")
    indexed = funnel.set_index("stage")["count"]
    missing = [label for _, label in FUNNEL_STAGES if label not in indexed.index]
    if missing:
        raise DataContractError(f"FAQ_FUNNEL is missing stages: {', '.join(missing)}")
    return {
        key: int(pd.to_numeric(indexed.loc[label], errors="raise"))
        for key, label in FUNNEL_STAGES
    }


def _load_and_validate() -> dict[str, object]:
    funnel = load_canonical_dataset("FAQ_FUNNEL")
    sources = load_canonical_dataset("FAQ_SOURCES")
    theme_summary = load_csv(THEME_SUMMARY_FILE)
    frozen = load_home_frozen_summaries()
    counts = _funnel_counts(funnel)

    require_columns(
        sources,
        ["subreddit", "posts", "comments", "observations"],
        "FAQ_SOURCES",
    )
    require_unique(sources, ["subreddit"], "FAQ_SOURCES")
    require_columns(
        theme_summary,
        ["brand", "executive_theme", "unique_comments"],
        "EXECUTIVE_THEME_BRAND_SUMMARY",
    )
    expected_themes = {title for title, _ in THEME_CARDS}
    if set(theme_summary["executive_theme"].astype(str)) != expected_themes:
        raise DataContractError(
            "Home theme groups do not match the frozen Executive Overview mapping"
        )

    population = frozen["production_population"]
    stage2a1 = frozen["stage2a1"]
    stage2b_population = frozen["stage2b_population"]
    stage2b_freeze = frozen["stage2b_freeze"]
    final_analysis = frozen["final_analysis_freeze"]
    require_columns(
        final_analysis,
        ["final_clean_observations", "time_period"],
        "FINAL_ANALYSIS_FREEZE",
    )
    if len(final_analysis) != 1:
        raise DataContractError("FINAL_ANALYSIS_FREEZE must contain one handoff row")

    checks = {
        "17,742 experience-bearing comments": (
            counts["experience_bearing"],
            _summary_value(
                population,
                "historical_stage1_experience_candidates",
                "2026_YTD_POPULATION_SUMMARY",
            ),
        ),
        "5,850 analysis-window comments": (
            counts["analysis_window"],
            _summary_value(
                population, "ytd_candidate_rows", "2026_YTD_POPULATION_SUMMARY"
            ),
        ),
        "5,850 Stage 2A-1 inputs": (
            counts["analysis_window"],
            _summary_value(
                stage2a1, "input_ytd_candidates", "STAGE2A1_PRODUCTION_SUMMARY"
            ),
        ),
        "3,696 usable comments": (
            counts["usable_comments"],
            _summary_value(stage2a1, "usable_rows", "STAGE2A1_PRODUCTION_SUMMARY"),
        ),
        "3,696 Stage 2B setup rows": (
            counts["usable_comments"],
            _summary_value(
                stage2b_population,
                "stage2A2_total_rows",
                "STAGE2B_POPULATION_SUMMARY",
            ),
        ),
        "2,215 known-attribution comments": (
            counts["known_comments"],
            _summary_value(
                stage2b_population,
                "stage2B_api_candidate_comments",
                "STAGE2B_POPULATION_SUMMARY",
            ),
        ),
        "2,215 production comments": (
            counts["known_comments"],
            _summary_value(
                stage2b_freeze,
                "production_comments",
                "STAGE2B_FINAL_FREEZE_SUMMARY",
            ),
        ),
        "6,003 extracted observations": (
            counts["extracted_observations"],
            _summary_value(
                stage2b_freeze,
                "production_observations",
                "STAGE2B_FINAL_FREEZE_SUMMARY",
            ),
        ),
        "5,997 clean observations": (
            counts["clean_observations"],
            _summary_value(
                stage2b_freeze,
                "final_clean_observations",
                "STAGE2B_FINAL_FREEZE_SUMMARY",
            ),
        ),
        "5,997 final-analysis handoff": (
            counts["clean_observations"],
            int(
                pd.to_numeric(
                    final_analysis.iloc[0]["final_clean_observations"],
                    errors="raise",
                )
            ),
        ),
        "5,997 source-summary observations": (
            counts["clean_observations"],
            int(pd.to_numeric(sources["observations"], errors="raise").sum()),
        ),
    }
    mismatches = [
        f"{label}: {left:,} vs {right:,}"
        for label, (left, right) in checks.items()
        if left != right
    ]
    if mismatches:
        raise DataContractError("Frozen Home count mismatch — " + "; ".join(mismatches))

    return {
        "counts": counts,
        "sources": sources.assign(
            comments=pd.to_numeric(sources["comments"], errors="raise").astype(int),
            observations=pd.to_numeric(
                sources["observations"], errors="raise"
            ).astype(int),
        ),
    }


if HOME_STYLE_FILE.is_file():
    st.html(f"<style>{HOME_STYLE_FILE.read_text(encoding='utf-8')}</style>")

try:
    data = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"Home cannot load its frozen data references safely. {error}")
    st.stop()

counts = data["counts"]
sources = data["sources"]
assert isinstance(counts, dict)
assert isinstance(sources, pd.DataFrame)

render_page_header(
    "Airport Lounge Experience Intelligence",
    "A 2026 YTD view of how Reddit users describe airport lounge experiences across Amex, Chase, Capital One and Delta.",
    eyebrow="REDDIT LOUNGE INTELLIGENCE",
)
st.markdown(
    '<div class="home-purpose-strip">The dashboard turns lounge-related Reddit feedback into brand, experience-theme, airport and customer-voice insights.</div>',
    unsafe_allow_html=True,
)

render_section_heading("Where do you want to start?")
navigation_cards = (
    (
        "overview",
        "01",
        "How does lounge feedback compare across brands?",
        "See the brand experience snapshot, five lounge-experience themes and how feedback has evolved from Jan–Aug 2026.",
        "pages/01_executive_overview.py",
        "View Executive Overview",
    ),
    (
        "airport",
        "02",
        "Where does lounge feedback stand out by airport?",
        "See every sufficiently supported airport, location-level positive and negative signals, and compare brands directly at the same airport.",
        "pages/04_airport_explorer.py",
        "Open Airport View",
    ),
    (
        "voices",
        "03",
        "What are travelers actually saying?",
        "Read representative positive, negative and mixed Reddit comments by brand and lounge-experience theme, or compare two brand voices side by side.",
        "pages/06_voice_of_customer.py",
        "Explore Customer Voices",
    ),
    (
        "methodology",
        "04",
        "How was the analysis built and how should I interpret it?",
        "See the full analysis funnel, classification approach, counting rules, validation, attribution logic and limitations.",
        "pages/07_methodology_faq.py",
        "Read Methodology",
    ),
)
with st.container(key="home-navigation-grid"):
    nav_columns = st.columns(4, gap="medium")
    for column, card in zip(nav_columns, navigation_cards, strict=True):
        with column:
            render_home_navigation_card(
                slug=card[0],
                number=card[1],
                question=card[2],
                description=card[3],
                target=card[4],
                cta=card[5],
            )

render_section_heading("What is behind the dashboard?")
render_snapshot_cards(
    [
        {
            "value": f"{counts['exploded_comments']:,}",
            "label": "Reddit comments reviewed",
            "support": "Comments collected across lounge-related Reddit discussions before experience filtering.",
        },
        {
            "value": f"{counts['experience_bearing']:,}",
            "label": "Comments with lounge-experience feedback",
            "support": "Comments describing a direct, second-hand or broader lounge experience.",
        },
        {
            "value": f"{counts['known_comments']:,}",
            "label": "Comments taken into detailed analysis",
            "support": "Comments with enough supported brand or lounge context for detailed experience extraction.",
        },
        {
            "value": f"{counts['clean_observations']:,}",
            "label": "Final experience observations",
            "support": "Final experience-level observations retained after quality checks.",
            "tooltip": "Final brand/lounge × experience-theme × sentiment observations retained after quality checks.",
        },
    ]
)

render_section_heading("How the dataset was narrowed")
render_methodology_funnel(counts)

render_section_heading("What parts of the lounge experience are analyzed?")
theme_markup = "".join(
    compact_html(
        f"""
        <article class="home-theme-card">
            <h3>{escape(title)}</h3>
            <p>{escape(description)}</p>
        </article>
        """
    )
    for title, description in THEME_CARDS
)
st.markdown(f'<div class="home-theme-grid">{theme_markup}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="home-inline-note">These are executive presentation groups. The underlying analysis retains the detailed experience areas separately.</div>',
    unsafe_allow_html=True,
)

render_section_heading("How to read the numbers")
reading_cards = (
    (
        "One comment is counted once",
        "Counts refer to unique qualifying Reddit comments in the displayed view.",
    ),
    (
        "Signals are combined within each view",
        "Each view combines the eligible experience signals within a comment before counting that comment once.",
    ),
    (
        "Counts can overlap",
        "One Reddit comment can discuss more than one brand or more than one part of the lounge experience, so brand and theme counts may overlap.",
    ),
    (
        "Quotes provide context",
        "Voice of Customer comments illustrate measured patterns. The number of quotes displayed does not indicate prevalence.",
    ),
)
reading_markup = "".join(
    compact_html(
        f"""
        <article class="home-interpret-card">
            <h3>{escape(title)}</h3><p>{escape(body)}</p>
        </article>
        """
    )
    for title, body in reading_cards
)
st.markdown(f'<div class="home-interpret-grid">{reading_markup}</div>', unsafe_allow_html=True)
with st.expander("About the analytical sentiment score", expanded=False):
    st.markdown(
        "Some deeper analytical calculations use a directional sentiment score from -100 to +100. "
        "It supports ranking, peer comparison and statistical testing, while the executive pages "
        "primarily show comment composition because it is easier to interpret directly.\n\n"
        "See FAQ / Methodology for the exact formula and confidence methodology."
    )

render_section_heading("Brands covered")
brand_markup = "".join(
    f'<span>{escape(ENTITY_SHORT_NAMES[brand])}</span>' for brand in HEADLINE_ISSUERS
)
st.markdown(f'<div class="home-brand-set">{brand_markup}</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="home-secondary-copy">The underlying analysis also retains physical lounge networks and access programs where attribution is supported.</p>',
    unsafe_allow_html=True,
)

render_section_heading(
    "Where the conversation comes from",
    f"{len(sources):,} Reddit communities contribute to the final clean analysis.",
)
st.markdown(
    '<p class="home-source-takeaway">Most discussion comes from a small number of brand and access-program communities.</p>',
    unsafe_allow_html=True,
)
render_source_ranking(sources)
st.markdown(
    '<div class="home-source-warning">Reddit discussion volume reflects where conversation was collected. It is not market share, customer population or brand popularity.</div>',
    unsafe_allow_html=True,
)

render_section_heading("Primary analytical unit")
st.markdown(
    compact_html(
        """
        <div class="home-scope-card">
            <strong>Individual Reddit comments</strong>
            <p>The dashboard primarily analyzes individual Reddit comments. Thread titles are used as supporting context when needed. Original post bodies were not systematically analyzed as separate experience units.</p>
            <small>See FAQ / Methodology for examples of comment-only and title-resolved attribution.</small>
        </div>
        """
    ),
    unsafe_allow_html=True,
)

render_section_heading("Before interpreting the results")
cautions = (
    "Reddit provides directional customer feedback, not a representative customer survey.",
    "More Reddit discussion does not mean more customers or greater market share.",
    "Missing airports indicate insufficient supported evidence, not neutral performance or the absence of a lounge.",
    "Monthly analysis uses the parent Reddit post date because individual comment timestamps were unavailable.",
    "UNKNOWN is preferred to assigning feedback to the wrong brand, lounge or airport.",
)
st.markdown(
    f'<ul class="home-caution-list">{"".join(f"<li>{escape(item)}</li>" for item in cautions)}</ul>',
    unsafe_allow_html=True,
)
st.caption("See FAQ / Methodology for the full methodology, validation and limitations.")
st.page_link(
    "pages/07_methodology_faq.py",
    label="Open FAQ / Methodology",
    icon=":material/info:",
)

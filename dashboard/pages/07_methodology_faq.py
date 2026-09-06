"""FAQ / Methodology — concise executive trust and interpretation layer."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from components.layout import render_page_header
from components.icons import title_icon_svg
from components.methodology import (
    compact_validation_table,
    render_example_card,
    render_info_cards,
)
from utils.data_loader import load_canonical_dataset
from utils.html import compact_html
from utils.validation import DataContractError, require_columns, require_unique


STYLE_FILE = Path(__file__).resolve().parents[1] / "assets" / "styles" / "methodology.css"
FAQ_METHODOLOGY_STATUS = "FAQ_METHODOLOGY_EXECUTIVE_REFINED"

FUNNEL_KEYS = (
    ("exploded_comments", "Exploded Reddit comment units"),
    ("experience_bearing", "Experience-bearing after Stage 1"),
    ("analysis_window", "2026 YTD production scope"),
    ("usable_comments", "Stage 2A-1 usable"),
    ("known_comments", "Known-attribution Stage 2B population"),
    ("extracted_observations", "Stage 2B extracted observations"),
    ("clean_observations", "Final clean observations"),
)
EXPECTED_COUNTS = {
    "exploded_comments": 61_413,
    "experience_bearing": 17_742,
    "analysis_window": 5_850,
    "usable_comments": 3_696,
    "known_comments": 2_215,
    "extracted_observations": 6_003,
    "clean_observations": 5_997,
}
def _section(anchor: str, title: str, description: str = "") -> None:
    paragraph = f"<p>{escape(description)}</p>" if description else ""
    icon = title_icon_svg(title, css_class="section-heading-icon")
    st.markdown(
        compact_html(
            f"""
            <div id="{escape(anchor)}" class="section-heading method-section-heading">
                <div>
                    <div class="section-heading-title">{icon}<h2>{escape(title)}</h2></div>
                    {paragraph}
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _load_and_validate() -> tuple[dict[str, int], pd.DataFrame, pd.DataFrame]:
    funnel = load_canonical_dataset("FAQ_FUNNEL")
    aspects = load_canonical_dataset("FAQ_ASPECT_GLOSSARY")
    examples = load_canonical_dataset("FAQ_EXAMPLES")

    require_columns(funnel, ["stage", "count", "definition"], "FAQ_FUNNEL")
    require_unique(funnel, ["stage"], "FAQ_FUNNEL")
    indexed = funnel.set_index("stage")["count"]
    missing = [stage for _, stage in FUNNEL_KEYS if stage not in indexed.index]
    if missing:
        raise DataContractError(f"FAQ_FUNNEL is missing: {', '.join(missing)}")
    counts = {
        key: int(pd.to_numeric(indexed.loc[stage], errors="raise"))
        for key, stage in FUNNEL_KEYS
    }
    if counts != EXPECTED_COUNTS:
        raise DataContractError(f"Frozen FAQ funnel changed: {counts}")

    require_columns(aspects, ["aspect", "definition"], "FAQ_ASPECT_GLOSSARY")
    require_columns(
        examples,
        [
            "comment_unit_id",
            "post_title",
            "comment_text",
            "post_url",
            "aspect",
            "sentiment",
            "evidence",
        ],
        "FAQ_EXAMPLES",
    )
    return counts, aspects, examples


def _example(comment_id: str) -> pd.DataFrame:
    rows = examples.loc[examples["comment_unit_id"].eq(comment_id)].copy()
    if rows.empty:
        raise DataContractError(f"Required FAQ example is missing: {comment_id}")
    return rows


def _render_example(
    comment_id: str,
    *,
    label: str,
    title: str,
    explanation: str,
    excerpt: str | None = None,
    include_aspects: tuple[str, ...] | None = None,
) -> None:
    group = _example(comment_id)
    first = group.iloc[0]
    if excerpt is not None and excerpt not in str(first["comment_text"]):
        raise DataContractError(f"Approved excerpt is not verbatim for {comment_id}")
    if include_aspects is not None:
        group = group.loc[group["aspect"].isin(include_aspects)]
        if group.empty:
            raise DataContractError(f"Approved example mappings are missing for {comment_id}")
    mappings = tuple(
        f"{str(row.aspect).replace('_', ' ').title()} → {str(row.sentiment).replace('_', ' ').title()}"
        for row in group[["aspect", "sentiment"]].drop_duplicates().itertuples(index=False)
    )
    render_example_card(
        label=label,
        title=title,
        comment=excerpt or str(first["comment_text"]),
        explanation=explanation,
        mappings=mappings,
        url=str(first["post_url"]),
    )


if STYLE_FILE.is_file():
    st.html(f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>")

try:
    counts, aspects, examples = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"FAQ / Methodology cannot load its frozen documentation sources safely. {error}")
    st.stop()

render_page_header(
    "FAQ / Methodology",
    "A concise guide to what was analyzed and how to interpret the results.",
    eyebrow="REDDIT LOUNGE INTELLIGENCE",
)
st.markdown(
    '<div class="method-intro-strip">The dashboard uses Reddit feedback from Jan–Aug 2026. These answers focus on the choices needed to read the results responsibly.</div>',
    unsafe_allow_html=True,
)

_section(
    "source-scope",
    "Analysis Scope & Approach",
    "The dashboard covers lounge-related Reddit discussion from Jan–Aug 2026.",
)
st.markdown(
    compact_html(
        """
        <div class="method-rule-box">
            <ul>
                <li>Lounge-related Reddit discussion was collected for the analysis period.</li>
                <li>Comments were filtered for actual lounge-experience content.</li>
                <li>Usable comments were attributed conservatively to brands, lounges and airports.</li>
                <li>Structured experience-theme and sentiment observations were then extracted.</li>
            </ul>
        </div>
        """
    ),
    unsafe_allow_html=True,
)

_section(
    "experience-filtering",
    "What Counts as Lounge Feedback",
    "A comment needed to express a defensible experience judgment.",
)
render_info_cards(
    (
        ("Included", "Direct, second-hand or broader observations about an actual lounge experience."),
        ("Removed", "Irrelevant discussion, access-only statements, question-only comments and text without enough usable experience detail."),
    )
)
_section(
    "attribution",
    "Brand, Lounge & Airport Attribution",
    "The analysis favors a conservative assignment over a confident-looking but unsupported one.",
)
st.markdown(
    compact_html(
        """
        <div class="method-rule-box">
            <ul>
                <li><strong>Comment first</strong> &mdash; a brand, lounge or airport named directly in the comment is used when clear.</li>
                <li><strong>Title as limited context</strong> &mdash; the post title can clarify a reference only when it points to one unambiguous target.</li>
                <li><strong>Unknown when uncertain</strong> &mdash; if the evidence does not support a reliable assignment, it remains unknown rather than being forced.</li>
            </ul>
        </div>
        """
    ),
    unsafe_allow_html=True,
)
with st.expander("See an approved title-context example", expanded=False):
    _render_example(
        "comment_0000527",
        label="Title-resolved context",
        title="The comment names Chase; the title supplies one clear airport",
        explanation="Chase is explicit in the comment, while Dulles/IAD is resolved from the uniquely targeted post title.",
    )

_section(
    "themes",
    "Experience Theme Framework",
    "Detailed experience areas are retained underneath a simpler executive presentation.",
)
st.markdown(
    compact_html(
        """
        <div class="method-rule-box">
            <ul>
                <li>Detailed lounge-experience areas were identified from the comments.</li>
                <li>Those areas were grouped into five executive themes for presentation.</li>
                <li>One comment may contribute to multiple themes when it discusses several parts of the experience.</li>
            </ul>
        </div>
        """
    ),
    unsafe_allow_html=True,
)
with st.expander("View the 19 detailed experience areas", expanded=False):
    detail = aspects.rename(columns={"aspect": "Experience area", "definition": "Plain-English definition"}).copy()
    compact_validation_table(detail)

_section(
    "sentiment-counting",
    "Sentiment & Comment Counting",
    "The dashboard keeps the customer voice readable without allowing repeated observations to overstate volume.",
)
st.markdown(
    compact_html(
        """
        <div class="method-rule-box">
            <ul>
                <li><strong>Positive</strong> — the comment expresses a favorable lounge-experience judgment.</li>
                <li><strong>Negative</strong> — the comment expresses an unfavorable lounge-experience judgment.</li>
                <li><strong>Mixed / neutral</strong> — the comment contains both directions or does not lean clearly positive or negative.</li>
                <li>One comment is counted once within the relevant brand, theme or airport view.</li>
                <li>A comment can contribute to more than one theme when it clearly discusses multiple parts of the experience.</li>
            </ul>
        </div>
        """
    ),
    unsafe_allow_html=True,
)
example_columns = st.columns(2, gap="medium")
with example_columns[0]:
    _render_example(
        "comment_0000413",
        label="Capital One · lounge experience",
        title="One clear experience judgment",
        explanation="The comment supports the displayed Capital One experience area and sentiment directly.",
        excerpt="The lounge is a great perk. I don't fly a ton, but using the lounge only 2x a year is easily $100 value and it's far more comfortable with it than without it.",
    )
with example_columns[1]:
    _render_example(
        "comment_0002181",
        label="Amex · food and beverage",
        title="Several judgments in one comment",
        explanation="The same comment supports separate experience areas and sentiments while remaining one comment in each relevant view.",
        excerpt="I generally find the food to be subpar. So, good place to grab a drink 🥃 if you have time.",
        include_aspects=("FOOD_QUALITY", "BEVERAGE_BAR"),
    )

_section(
    "interpretation",
    "How to Read the Results",
    "Use the dashboard to identify directional experience signals and questions worth investigating.",
)
st.markdown(
    compact_html(
        """
        <div class="method-rule-box interpretation">
            <ul>
                <li>Reddit feedback is directional, not representative of all lounge customers.</li>
                <li>Discussion volume is not market share, preference or commercial scale.</li>
                <li>Evidence volume varies by brand, airport and experience theme.</li>
                <li>Observed patterns are descriptive and do not establish causality.</li>
            </ul>
        </div>
        """
    ),
    unsafe_allow_html=True,
)
st.caption("Examples and displayed results reflect the fixed Jan–Aug 2026 analysis.")

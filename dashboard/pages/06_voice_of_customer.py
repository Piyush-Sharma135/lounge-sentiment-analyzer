"""Voice of Customer - curated evidence gallery."""

from __future__ import annotations

from html import escape
from pathlib import Path
import re

import pandas as pd
import streamlit as st

from components.layout import render_page_header, render_section_heading
from utils.assets import brand_logo_img
from utils.constants import DATA_DIR, ENTITY_SHORT_NAMES, HEADLINE_ISSUERS
from utils.data_loader import load_csv
from utils.html import compact_html
from utils.styling import apply_base_styles
from utils.validation import DataContractError, require_columns, require_unique


EVIDENCE_FILE = DATA_DIR / "58_voc_display_public.csv"
POPULATION_FILE = DATA_DIR / "58_voc_population_public.csv"
QA_FILE = DATA_DIR / "56_voc_qa.csv"
VOC_STYLE_FILE = Path(__file__).resolve().parents[1] / "assets" / "styles" / "voc.css"

BRAND_OPTIONS = ("ALL", *HEADLINE_ISSUERS)
THEMES = (
    "General Lounge Experience",
    "Access & Capacity",
    "Food & Beverage",
    "Service & Upkeep",
    "Space, Amenities & Convenience",
)
THEME_OPTIONS = ("ALL", *THEMES)
BRAND_ORDER = {brand: index for index, brand in enumerate(HEADLINE_ISSUERS)}
BRAND_MENTION_PATTERNS = {
    "AMEX": re.compile(r"\b(?:amex|american express|centurion)\b", re.I),
    "CHASE": re.compile(r"\b(?:chase|sapphire)\b", re.I),
    "CAPITAL_ONE": re.compile(r"\b(?:capital\s*one|venture\s*x|c1 lounge)\b", re.I),
    "DELTA": re.compile(r"\b(?:delta|sky\s*club|skyclub)\b", re.I),
}
MONTH_LABELS = {
    f"2026-{month:02d}": pd.Timestamp(2026, month, 1).strftime("%b 2026")
    for month in range(1, 9)
}


apply_base_styles()
if VOC_STYLE_FILE.is_file():
    st.html(f"<style>{VOC_STYLE_FILE.read_text(encoding='utf-8')}</style>")


def _brand_label(value: str) -> str:
    return "All brands" if value == "ALL" else ENTITY_SHORT_NAMES.get(value, value)


def _theme_label(value: str) -> str:
    return "All themes" if value == "ALL" else value


def _load_and_validate() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    evidence = load_csv(EVIDENCE_FILE)
    population = load_csv(POPULATION_FILE)
    qa = load_csv(QA_FILE)
    require_columns(
        evidence,
        [
            "comment_unit_id",
            "brand",
            "brand_display",
            "executive_theme",
            "aspect",
            "detailed_aspect",
            "sentiment_group",
            "display_text",
            "display_priority",
            "airport_code",
            "month",
            "subreddit",
            "post_url",
            "cross_brand_comparison",
        ],
        "VOC_EXECUTIVE_EVIDENCE",
    )
    require_columns(
        population,
        [
            "scope_brand",
            "executive_theme",
            "sentiment_group",
            "month",
            "airport_code",
            "detailed_aspects",
            "unique_comments",
        ],
        "VOC_POPULATION_COMMENTS",
    )
    require_columns(qa, ["check", "status"], "VOC_QA")
    require_unique(
        population,
        [
            "scope_brand",
            "executive_theme",
            "sentiment_group",
            "month",
            "airport_code",
            "detailed_aspects",
        ],
        "VOC_POPULATION_COMMENTS",
    )
    if set(evidence["executive_theme"].dropna()) != set(THEMES):
        raise DataContractError("Voice evidence does not match the approved five themes.")
    if set(population["executive_theme"].dropna()) != set(THEMES):
        raise DataContractError("Voice population does not match the approved five themes.")
    if not qa["status"].eq("PASS").all():
        failed = qa.loc[qa["status"].ne("PASS"), "check"].astype(str).tolist()
        raise DataContractError(f"Voice presentation QA failed: {', '.join(failed)}")
    if not evidence["post_url"].astype(str).str.startswith(
        "https://www.reddit.com/"
    ).all():
        raise DataContractError("Voice evidence must use public Reddit post links.")
    evidence["airport_code"] = evidence["airport_code"].fillna("")
    population["airport_code"] = population["airport_code"].fillna("")
    population["unique_comments"] = pd.to_numeric(
        population["unique_comments"], errors="raise"
    ).astype(int)
    if (population["unique_comments"] <= 0).any():
        raise DataContractError("Voice population contains an invalid aggregate count.")
    return evidence, population, qa


def _filter_population(
    population: pd.DataFrame,
    brand: str,
    theme: str,
) -> pd.DataFrame:
    selected = population.loc[population["scope_brand"].eq(brand)].copy()
    if theme != "ALL":
        selected = selected.loc[selected["executive_theme"].eq(theme)]
    return selected


def _filter_evidence(
    evidence: pd.DataFrame,
    brand: str,
    theme: str,
    airport: str,
    month: str,
) -> pd.DataFrame:
    selected = evidence.copy()
    if theme != "ALL":
        selected = selected.loc[selected["executive_theme"].eq(theme)]
    if brand != "ALL":
        selected = selected.loc[selected["brand"].eq(brand)]
    if airport != "ALL":
        selected = selected.loc[selected["airport_code"].eq(airport)]
    if month != "ALL":
        selected = selected.loc[selected["month"].eq(month)]
    return selected


def _select_quotes(
    candidates: pd.DataFrame,
    sentiments: tuple[str, ...],
    limit: int,
    used_ids: set[str],
    balance_brands: bool,
) -> pd.DataFrame:
    selected = candidates.loc[
        candidates["sentiment_group"].isin(sentiments)
        & ~candidates["comment_unit_id"].astype(str).isin(used_ids)
    ].copy()
    if selected.empty:
        return selected
    sentiment_order = {sentiment: index for index, sentiment in enumerate(sentiments)}
    selected["brand_order"] = selected["brand"].map(BRAND_ORDER)
    selected["sentiment_order"] = selected["sentiment_group"].map(sentiment_order)
    selected = selected.sort_values(
        [
            "display_priority",
            "sentiment_order",
            "brand_order",
            "detailed_aspect",
            "comment_unit_id",
        ]
    )
    chosen: list[object] = []
    chosen_comment_ids: set[str] = set()
    if balance_brands:
        for brand in HEADLINE_ISSUERS:
            brand_rows = selected.loc[selected["brand"].eq(brand)]
            for index, row in brand_rows.iterrows():
                comment_id = str(row["comment_unit_id"])
                if comment_id not in chosen_comment_ids and len(chosen) < limit:
                    chosen.append(index)
                    chosen_comment_ids.add(comment_id)
                    break
    for index, row in selected.iterrows():
        if len(chosen) >= limit:
            break
        comment_id = str(row["comment_unit_id"])
        if comment_id not in chosen_comment_ids:
            chosen.append(index)
            chosen_comment_ids.add(comment_id)
    result = selected.loc[chosen].copy()
    used_ids.update(result["comment_unit_id"].astype(str))
    return result


def _mentioned_brands(text: str) -> set[str]:
    return {
        brand
        for brand, pattern in BRAND_MENTION_PATTERNS.items()
        if pattern.search(text)
    }


def _quote_card(row: pd.Series, compact: bool = False) -> str:
    theme = str(row["executive_theme"])
    airport = str(row.get("airport_code", "")).strip()
    metadata = [str(row["brand_display"]), theme]
    if airport and airport not in {"nan", "MULTIPLE"}:
        metadata.append(airport)
    metadata_markup = " &middot; ".join(escape(value) for value in metadata)
    aspect = str(row.get("detailed_aspect", "")).strip()
    aspect_markup = ""
    if theme != "General Lounge Experience" and aspect and aspect != "nan":
        aspect_markup = f'<span class="voc-quote-aspect">{escape(aspect)}</span>'
    cross_brand = len(_mentioned_brands(str(row["display_text"]))) >= 2
    cross_badge = (
        '<span class="voc-cross-badge">Cross-brand comparison</span>'
        if cross_brand
        else ""
    )
    sentiment_class = {
        "POSITIVE": "positive",
        "NEGATIVE": "negative",
        "MIXED_NEUTRAL": "mixed",
    }.get(str(row["sentiment_group"]), "mixed")
    month = MONTH_LABELS.get(str(row["month"]), str(row["month"]))
    compact_class = " compact" if compact else ""
    return compact_html(
        f"""
        <article class="voc-quote-card {sentiment_class}{compact_class}" data-comment-id="{escape(str(row['comment_unit_id']))}">
            <div class="voc-quote-meta">{metadata_markup}</div>
            <div class="voc-quote-tags">{aspect_markup}{cross_badge}</div>
            <blockquote>&ldquo;{escape(str(row['display_text']))}&rdquo;</blockquote>
            <div class="voc-quote-footer">
                <span>{escape(month)} &middot; r/{escape(str(row['subreddit']))}</span>
                <a href="{escape(str(row['post_url']))}" target="_blank" rel="noopener noreferrer">View Reddit post&nbsp;<span aria-hidden="true">&nearr;</span></a>
            </div>
        </article>
        """
    )


def _render_voice_gallery(
    candidates: pd.DataFrame,
    sentiments: tuple[str, ...],
    limit: int,
    used_ids: set[str],
    balance_brands: bool,
    empty_copy: str,
    tone: str,
) -> int:
    selected = _select_quotes(
        candidates,
        sentiments,
        limit,
        used_ids,
        balance_brands,
    )
    if selected.empty:
        st.markdown(
            f'<div class="voc-empty {tone}">{escape(empty_copy)}</div>',
            unsafe_allow_html=True,
        )
        return 0
    cards = "".join(_quote_card(row) for _, row in selected.iterrows())
    st.markdown(
        f'<div class="voc-voice-grid {tone}">{cards}</div>',
        unsafe_allow_html=True,
    )
    return len(selected)


def _comparison_side(
    brand: str,
    candidates: pd.DataFrame,
    used_ids: set[str],
) -> str:
    brand_candidates = candidates.loc[candidates["brand"].eq(brand)].copy()
    brand_candidates = brand_candidates.loc[
        ~brand_candidates["cross_brand_comparison"]
        .astype(str)
        .str.lower()
        .isin({"true", "1", "yes"})
        & ~brand_candidates["display_text"].astype(str).map(
            lambda text: len(_mentioned_brands(text)) >= 2
        )
    ]
    positive = _select_quotes(
        brand_candidates,
        ("POSITIVE",),
        2,
        used_ids,
        False,
    )
    negative_mixed = _select_quotes(
        brand_candidates,
        ("NEGATIVE", "MIXED_NEUTRAL"),
        2,
        used_ids,
        False,
    )
    positive_markup = (
        "".join(_quote_card(row, compact=True) for _, row in positive.iterrows())
        if not positive.empty
        else '<div class="voc-empty compact">No additional positive voice is available.</div>'
    )
    negative_markup = (
        "".join(
            _quote_card(row, compact=True) for _, row in negative_mixed.iterrows()
        )
        if not negative_mixed.empty
        else '<div class="voc-empty compact">No additional negative or mixed voice is available.</div>'
    )
    return compact_html(
        f"""
        <section class="voc-compare-side">
            <h3>{brand_logo_img(brand)}<span>{escape(_brand_label(brand))}</span></h3>
            <div class="voc-compare-group positive">
                <span>Representative positive voices</span>
                <div class="voc-compare-quotes">{positive_markup}</div>
            </div>
            <div class="voc-compare-group negative">
                <span>Representative negative / mixed voices</span>
                <div class="voc-compare-quotes">{negative_markup}</div>
            </div>
        </section>
        """
    )


try:
    evidence_rows, population_rows, voc_qa = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"Voice of Customer cannot load its presentation data. {error}")
    st.stop()

render_page_header(
    "Voice of Customer",
    "The real traveler comments behind the lounge experience patterns.",
)
st.markdown(
    '<div class="voc-hero-note">Explore representative Reddit voices by brand, theme, airport and month.</div>',
    unsafe_allow_html=True,
)

render_section_heading(
    "Explore Customer Voices",
    "Filter the representative evidence by brand and experience context.",
)
filter_brand, filter_theme = st.columns(2, gap="large")
with filter_brand:
    selected_brand = st.selectbox(
        "Brand",
        BRAND_OPTIONS,
        index=0,
        format_func=_brand_label,
        key="voc_brand",
    )
with filter_theme:
    selected_theme = st.selectbox(
        "Experience Theme",
        THEME_OPTIONS,
        index=0,
        format_func=_theme_label,
        key="voc_theme",
    )

base_population = _filter_population(
    population_rows,
    selected_brand,
    selected_theme,
)
with st.expander("More filters", expanded=False):
    more_airport, more_month = st.columns(2, gap="large")
    airport_values = sorted(
        value
        for value in base_population["airport_code"].dropna().astype(str).unique()
        if value and value != "MULTIPLE"
    )
    with more_airport:
        selected_airport = st.selectbox(
            "Airport",
            ("ALL", *airport_values),
            format_func=lambda value: "All airports" if value == "ALL" else value,
            key="voc_airport",
        )
    with more_month:
        selected_month = st.selectbox(
            "Month",
            ("ALL", *MONTH_LABELS),
            format_func=lambda value: (
                "All months" if value == "ALL" else MONTH_LABELS[value]
            ),
            key="voc_month",
        )

selected_evidence = _filter_evidence(
    evidence_rows,
    selected_brand,
    selected_theme,
    selected_airport,
    selected_month,
)
context_parts = [_brand_label(selected_brand), _theme_label(selected_theme)]
if selected_airport != "ALL":
    context_parts.append(selected_airport)
if selected_month != "ALL":
    context_parts.append(MONTH_LABELS[selected_month])
st.markdown(
    f'<div class="voc-filter-context">Showing voices for {" &middot; ".join(escape(part) for part in context_parts)}</div>',
    unsafe_allow_html=True,
)

used_comment_ids: set[str] = set()
balance_brands = selected_brand == "ALL"

render_section_heading(
    "Positive Voices",
    "Representative comments describing what travelers valued.",
)
st.markdown(
    '<div class="voc-context-note">Quotes are representative examples selected from the filtered comment population; they do not indicate prevalence by themselves.</div>',
    unsafe_allow_html=True,
)
_render_voice_gallery(
    selected_evidence,
    ("POSITIVE",),
    3,
    used_comment_ids,
    balance_brands,
    "No representative positive voices are available for this selection.",
    "positive",
)

render_section_heading(
    "Negative Voices",
    "Representative comments describing the main experience frictions.",
)
_render_voice_gallery(
    selected_evidence,
    ("NEGATIVE",),
    3,
    used_comment_ids,
    balance_brands,
    "No representative negative voices are available for this selection.",
    "negative",
)

render_section_heading(
    "Mixed / Nuanced Voices",
    "Comments where travelers describe both strengths and weaknesses.",
)
_render_voice_gallery(
    selected_evidence,
    ("MIXED_NEUTRAL",),
    2,
    used_comment_ids,
    balance_brands,
    "No mixed or nuanced representative comments are available for this selection.",
    "mixed",
)

render_section_heading(
    "Compare Customer Voices",
    "Place representative comments from two brands side by side within the same experience theme.",
)
compare_a_column, compare_b_column, compare_theme_column = st.columns(3, gap="large")
default_a = selected_brand if selected_brand != "ALL" else "AMEX"
with compare_a_column:
    brand_a = st.selectbox(
        "Brand A",
        HEADLINE_ISSUERS,
        index=HEADLINE_ISSUERS.index(default_a),
        format_func=_brand_label,
        key="voc_compare_a",
    )
brand_b_options = tuple(brand for brand in HEADLINE_ISSUERS if brand != brand_a)
default_b = "CHASE" if "CHASE" in brand_b_options else brand_b_options[0]
with compare_b_column:
    brand_b = st.selectbox(
        "Brand B",
        brand_b_options,
        index=brand_b_options.index(default_b),
        format_func=_brand_label,
        key="voc_compare_b",
    )
with compare_theme_column:
    comparison_theme = st.selectbox(
        "Experience Theme",
        THEME_OPTIONS,
        index=THEME_OPTIONS.index(selected_theme),
        format_func=_theme_label,
        key="voc_compare_theme",
    )

comparison_evidence = _filter_evidence(
    evidence_rows,
    "ALL",
    comparison_theme,
    selected_airport,
    selected_month,
)
comparison_brand_set = {brand_a, brand_b}
cross_brand_rows = comparison_evidence.loc[
    comparison_evidence["cross_brand_comparison"]
    .astype(str)
    .str.lower()
    .isin({"true", "1", "yes"})
    & ~comparison_evidence["comment_unit_id"].astype(str).isin(used_comment_ids)
    & comparison_evidence["display_text"].astype(str).map(
        lambda value: comparison_brand_set <= _mentioned_brands(value)
    )
].sort_values(["display_priority", "comment_unit_id"])
cross_brand_markup = ""
if not cross_brand_rows.empty:
    cross_row = cross_brand_rows.drop_duplicates("comment_unit_id").iloc[0]
    used_comment_ids.add(str(cross_row["comment_unit_id"]))
    cross_brand_markup = compact_html(
        f"""
        <div class="voc-explicit-comparison">
            <span>Explicit cross-brand evidence</span>
            {_quote_card(cross_row, compact=True)}
        </div>
        """
    )

side_a = _comparison_side(
    brand_a,
    comparison_evidence,
    used_comment_ids,
)
side_b = _comparison_side(
    brand_b,
    comparison_evidence,
    used_comment_ids,
)
st.markdown(
    f'<div class="voc-compare-grid">{side_a}{side_b}</div>{cross_brand_markup}',
    unsafe_allow_html=True,
)

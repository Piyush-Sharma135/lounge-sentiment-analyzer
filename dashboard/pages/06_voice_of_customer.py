"""Voice of Customer - curated qualitative evidence workspace."""

from __future__ import annotations

from html import escape
from pathlib import Path
import re

import pandas as pd
import streamlit as st

from components.layout import render_page_header, render_section_heading
from utils.constants import DATA_DIR, ENTITY_SHORT_NAMES, HEADLINE_ISSUERS
from utils.data_loader import load_csv
from utils.html import compact_html
from utils.styling import apply_base_styles
from utils.validation import DataContractError, require_columns, require_unique


EVIDENCE_FILE = DATA_DIR / "58_voc_display_public.csv"
POPULATION_FILE = DATA_DIR / "58_voc_population_public.csv"
QA_FILE = DATA_DIR / "56_voc_qa.csv"
VOC_STYLE_FILE = Path(__file__).resolve().parents[1] / "assets" / "styles" / "voc.css"
VOICE_OF_CUSTOMER_STATUS = "VOICE_OF_CUSTOMER_FINAL_FROZEN"

BRAND_OPTIONS = ("ALL", *HEADLINE_ISSUERS)
THEMES = (
    "General Lounge Experience",
    "Access & Capacity",
    "Food & Beverage",
    "Service & Upkeep",
    "Space, Amenities & Convenience",
)
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
    airport: str,
    month: str,
) -> pd.DataFrame:
    selected = population.loc[
        population["scope_brand"].eq(brand)
        & population["executive_theme"].eq(theme)
    ].copy()
    if airport != "ALL":
        selected = selected.loc[selected["airport_code"].eq(airport)]
    if month != "ALL":
        selected = selected.loc[selected["month"].eq(month)]
    return selected


def _filter_evidence(
    evidence: pd.DataFrame,
    brand: str,
    theme: str,
    airport: str,
    month: str,
) -> pd.DataFrame:
    selected = evidence.loc[evidence["executive_theme"].eq(theme)].copy()
    if brand != "ALL":
        selected = selected.loc[selected["brand"].eq(brand)]
    if airport != "ALL":
        selected = selected.loc[selected["airport_code"].eq(airport)]
    if month != "ALL":
        selected = selected.loc[selected["month"].eq(month)]
    return selected


def _most_discussed_aspect(population: pd.DataFrame, theme: str) -> str:
    if theme == "General Lounge Experience":
        return "Overall lounge experience"
    weighted = population.loc[
        population["detailed_aspects"].notna(),
        ["detailed_aspects", "unique_comments"],
    ].copy()
    weighted["detailed_aspects"] = weighted["detailed_aspects"].astype(str).str.split(
        " | ", regex=False
    )
    weighted = weighted.explode("detailed_aspects")
    if weighted.empty:
        return "Not enough evidence"
    counts = weighted.groupby("detailed_aspects")["unique_comments"].sum()
    aspect = str(sorted(counts.loc[counts.eq(counts.max())].index)[0])
    labels = dict(
        zip(
            evidence_rows["aspect"].astype(str),
            evidence_rows["detailed_aspect"].astype(str),
        )
    )
    return labels.get(aspect, aspect.replace("_", " ").title())


def _sentiment_bar(positive: int, negative: int, mixed: int) -> str:
    total = max(positive + negative + mixed, 1)
    return compact_html(
        f"""
        <div class="voc-sentiment-bar" aria-label="{positive} positive, {negative} negative, {mixed} mixed or neutral comments">
            <i class="positive" style="width:{positive / total * 100:.3f}%"></i>
            <i class="negative" style="width:{negative / total * 100:.3f}%"></i>
            <i class="mixed" style="width:{mixed / total * 100:.3f}%"></i>
        </div>
        """
    )


def _render_snapshot(selected: pd.DataFrame, theme: str) -> dict[str, int]:
    counts = selected.groupby("sentiment_group")["unique_comments"].sum()
    positive = int(counts.get("POSITIVE", 0))
    negative = int(counts.get("NEGATIVE", 0))
    mixed = int(counts.get("MIXED_NEUTRAL", 0))
    total = int(selected["unique_comments"].sum())
    if positive + negative + mixed != total:
        raise DataContractError("Selected Voice population does not pass comment identity.")
    aspect = _most_discussed_aspect(selected, theme)
    secondary_card = ""
    snapshot_class = " single" if theme == "General Lounge Experience" else ""
    if theme != "General Lounge Experience":
        secondary_card = compact_html(
            f"""
            <article class="voc-snapshot-aspect"><span>Most discussed subtheme</span><strong>{escape(aspect)}</strong></article>
            """
        )
    st.markdown(
        compact_html(
            f"""
            <div class="voc-snapshot{snapshot_class}">
                <article class="voc-snapshot-main">
                    <div><strong>{total}</strong><span>qualifying comments</span></div>
                    {_sentiment_bar(positive, negative, mixed)}
                    <p><b class="positive">{positive} positive</b><i>&middot;</i><b class="negative">{negative} negative</b><i>&middot;</i><b class="mixed">{mixed} mixed/neutral</b></p>
                </article>
                {secondary_card}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    if 0 < total < 10:
        st.markdown(
            '<div class="voc-limited">Limited qualitative evidence for this selection.</div>',
            unsafe_allow_html=True,
        )
    return {
        "POSITIVE": positive,
        "NEGATIVE": negative,
        "MIXED_NEUTRAL": mixed,
        "TOTAL": total,
    }


def _select_quotes(
    candidates: pd.DataFrame,
    sentiment: str,
    limit: int,
    used_ids: set[str],
    balance_brands: bool,
) -> pd.DataFrame:
    selected = candidates.loc[
        candidates["sentiment_group"].eq(sentiment)
        & ~candidates["comment_unit_id"].astype(str).isin(used_ids)
    ].copy()
    if selected.empty:
        return selected
    selected["brand_order"] = selected["brand"].map(BRAND_ORDER)
    selected = selected.sort_values(
        ["display_priority", "brand_order", "detailed_aspect", "comment_unit_id"]
    )
    chosen: list[int] = []
    chosen_comment_ids: set[str] = set()
    if balance_brands:
        for brand in HEADLINE_ISSUERS:
            rows = selected.loc[selected["brand"].eq(brand)]
            for index, row in rows.iterrows():
                comment_id = str(row["comment_unit_id"])
                if comment_id not in chosen_comment_ids and len(chosen) < limit:
                    chosen.append(int(index))
                    chosen_comment_ids.add(comment_id)
                    break
    for index in selected.index:
        if len(chosen) >= limit:
            break
        comment_id = str(selected.loc[index, "comment_unit_id"])
        if comment_id not in chosen_comment_ids:
            chosen.append(int(index))
            chosen_comment_ids.add(comment_id)
    result = selected.loc[chosen].copy()
    used_ids.update(result["comment_unit_id"].astype(str))
    return result


def _mentioned_brands(text: str) -> set[str]:
    return {
        brand for brand, pattern in BRAND_MENTION_PATTERNS.items()
        if pattern.search(text)
    }


def _quote_card(
    row: pd.Series,
    compact: bool = False,
    evidence_label: str = "",
) -> str:
    airport = str(row.get("airport_code", "")).strip()
    metadata = [
        str(row["brand_display"]).upper(),
        str(row["executive_theme"]).upper(),
    ]
    if str(row["executive_theme"]) != "General Lounge Experience":
        metadata.append(str(row["detailed_aspect"]).upper())
    if airport and airport != "nan":
        metadata.append(airport)
    cross_brand = len(_mentioned_brands(str(row["display_text"]))) >= 2
    cross_badge = (
        '<span class="voc-cross-badge">Cross-brand comparison</span>'
        if cross_brand
        else ""
    )
    month = MONTH_LABELS.get(str(row["month"]), str(row["month"]))
    compact_class = " compact" if compact else ""
    evidence_label_markup = (
        f'<span class="voc-evidence-role">{escape(evidence_label)}</span>'
        if evidence_label
        else ""
    )
    return compact_html(
        f"""
        <article class="voc-quote-card{compact_class}" data-comment-id="{escape(str(row['comment_unit_id']))}">
            {evidence_label_markup}
            <div class="voc-quote-meta">{escape(' · '.join(metadata))}</div>
            {cross_badge}
            <blockquote>“{escape(str(row['display_text']))}”</blockquote>
            <div class="voc-quote-footer"><span>{escape(month)} · r/{escape(str(row['subreddit']))}</span><a href="{escape(str(row['post_url']))}" target="_blank" rel="noopener noreferrer">View Reddit source ↗</a></div>
        </article>
        """
    )


def _render_tab_quotes(
    label: str,
    candidates: pd.DataFrame,
    sentiment: str,
    limit: int,
    used_ids: set[str],
    balance_brands: bool,
) -> int:
    selected = _select_quotes(
        candidates, sentiment, limit, used_ids, balance_brands
    )
    if selected.empty:
        st.markdown(
            f'<div class="voc-empty">No curated {escape(label.lower())} comment is available for this selection.</div>',
            unsafe_allow_html=True,
        )
        return 0
    cards = "".join(_quote_card(row) for _, row in selected.iterrows())
    st.markdown(f'<div class="voc-tab-stack">{cards}</div>', unsafe_allow_html=True)
    return len(selected)


def _brand_population(
    population: pd.DataFrame,
    brand: str,
    theme: str,
    airport: str,
    month: str,
) -> pd.DataFrame:
    return _filter_population(population, brand, theme, airport, month)


def _comparison_sentence(
    brand_a: str,
    brand_b: str,
    population_a: pd.DataFrame,
    population_b: pd.DataFrame,
    theme: str,
) -> str:
    name_a = _brand_label(brand_a)
    name_b = _brand_label(brand_b)
    aspect_a = _most_discussed_aspect(population_a, theme)
    aspect_b = _most_discussed_aspect(population_b, theme)
    total_a = int(population_a["unique_comments"].sum())
    total_b = int(population_b["unique_comments"].sum())
    positive_a = (
        int(population_a.loc[population_a["sentiment_group"].eq("POSITIVE"), "unique_comments"].sum())
        / total_a
        if total_a
        else 0
    )
    positive_b = (
        int(population_b.loc[population_b["sentiment_group"].eq("POSITIVE"), "unique_comments"].sum())
        / total_b
        if total_b
        else 0
    )
    if aspect_a != aspect_b and "Not enough" not in f"{aspect_a}{aspect_b}":
        return (
            f"{name_a} comments most often focus on {aspect_a.lower()}, while "
            f"{name_b} comments most often focus on {aspect_b.lower()}."
        )
    if abs(positive_a - positive_b) >= 0.05:
        stronger = name_a if positive_a > positive_b else name_b
        other = name_b if positive_a > positive_b else name_a
        return (
            f"{stronger} has a higher share of positive feedback than {other} "
            f"in the selected comment population."
        )
    return f"{name_a} and {name_b} show a broadly similar positive-feedback mix for this selection."


def _comparison_side(
    brand: str,
    population: pd.DataFrame,
    candidates: pd.DataFrame,
    theme: str,
    used_ids: set[str],
) -> str:
    counts = population.groupby("sentiment_group")["unique_comments"].sum()
    positive = int(counts.get("POSITIVE", 0))
    negative = int(counts.get("NEGATIVE", 0))
    mixed = int(counts.get("MIXED_NEUTRAL", 0))
    aspects = _most_discussed_aspect(population, theme)
    focus_markup = ""
    if theme != "General Lounge Experience":
        focus_markup = compact_html(
            f"""
            <p class="voc-compare-focus"><span>Most discussed subtheme</span><strong>{escape(aspects)}</strong></p>
            """
        )
    quote_rows: list[tuple[str, pd.Series]] = []
    brand_candidates = candidates.loc[
        candidates["brand"].eq(brand)
        & ~candidates["cross_brand_comparison"]
        .astype(str)
        .str.lower()
        .isin({"true", "1", "yes"})
    ]
    sentiment_order = sorted(
        SENTIMENT_LABELS,
        key=lambda sentiment: (-int(counts.get(sentiment, 0)), SENTIMENT_LABELS[sentiment]),
    )
    for sentiment in sentiment_order:
        selected = _select_quotes(
            brand_candidates,
            sentiment,
            1,
            used_ids,
            False,
        )
        if not selected.empty:
            evidence_label = (
                "Representative positive voice"
                if sentiment == "POSITIVE"
                else "Representative negative / mixed voice"
            )
            quote_rows.append((evidence_label, selected.iloc[0]))
        if len(quote_rows) == 2:
            break
    quotes = "".join(
        _quote_card(row, compact=True, evidence_label=evidence_label)
        for evidence_label, row in quote_rows
    )
    if not quotes:
        quotes = '<div class="voc-empty compact">No additional curated comment is available.</div>'
    return compact_html(
        f"""
        <div class="voc-compare-side">
            <h3>{escape(_brand_label(brand))}</h3>
            <div class="voc-compare-counts"><strong>{positive + negative + mixed}</strong><span>comments</span><b class="positive">{positive} positive</b><b class="negative">{negative} negative</b><b class="mixed">{mixed} mixed/neutral</b></div>
            {_sentiment_bar(positive, negative, mixed)}
            {focus_markup}
            <div class="voc-compare-quotes">{quotes}</div>
        </div>
        """
    )


SENTIMENT_LABELS = {
    "POSITIVE": "Positive",
    "NEGATIVE": "Negative",
    "MIXED_NEUTRAL": "Mixed/neutral",
}


try:
    evidence_rows, population_rows, voc_qa = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"Voice of Customer cannot load its presentation data. {error}")
    st.stop()

render_page_header(
    "Voice of Customer",
    "Explore the Reddit comments behind the lounge-experience patterns.",
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
        "Experience theme",
        THEMES,
        index=0,
        key="voc_theme",
    )

base_population = population_rows.loc[
    population_rows["scope_brand"].eq(selected_brand)
    & population_rows["executive_theme"].eq(selected_theme)
]
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
            format_func=lambda value: "All months" if value == "ALL" else MONTH_LABELS[value],
            key="voc_month",
        )

selected_population = _filter_population(
    population_rows,
    selected_brand,
    selected_theme,
    selected_airport,
    selected_month,
)
selected_evidence = _filter_evidence(
    evidence_rows,
    selected_brand,
    selected_theme,
    selected_airport,
    selected_month,
)

render_section_heading(
    "Feedback behind these voices",
    "The measured comment population behind the representative examples below.",
)
snapshot_counts = _render_snapshot(selected_population, selected_theme)

st.markdown(
    '<div class="voc-context-note">The comments below are representative examples. The sentiment counts above show prevalence within the measured dataset; the number of quotes displayed does not.</div>',
    unsafe_allow_html=True,
)

used_comment_ids: set[str] = set()
balance = selected_brand == "ALL"
positive_tab, negative_tab, mixed_tab = st.tabs(
    [
        f"Positive ({snapshot_counts['POSITIVE']})",
        f"Negative ({snapshot_counts['NEGATIVE']})",
        f"Mixed / nuanced ({snapshot_counts['MIXED_NEUTRAL']})",
    ]
)
with positive_tab:
    _render_tab_quotes(
        "positive",
        selected_evidence,
        "POSITIVE",
        4,
        used_comment_ids,
        balance,
    )
with negative_tab:
    _render_tab_quotes(
        "negative",
        selected_evidence,
        "NEGATIVE",
        4,
        used_comment_ids,
        balance,
    )
with mixed_tab:
    _render_tab_quotes(
        "mixed or nuanced",
        selected_evidence,
        "MIXED_NEUTRAL",
        4,
        used_comment_ids,
        balance,
    )

render_section_heading(
    "Compare brand voices",
    f"Compare how two brands are discussed within {selected_theme}.",
)
compare_a_column, compare_b_column = st.columns(2, gap="large")
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

population_a = _brand_population(
    population_rows, brand_a, selected_theme, selected_airport, selected_month
)
population_b = _brand_population(
    population_rows, brand_b, selected_theme, selected_airport, selected_month
)
compare_evidence = _filter_evidence(
    evidence_rows, "ALL", selected_theme, selected_airport, selected_month
)
comparison_brand_set = {brand_a, brand_b}
cross_brand_rows = compare_evidence.loc[
    compare_evidence["cross_brand_comparison"].astype(str).str.lower().isin({"true", "1", "yes"})
    & ~compare_evidence["comment_unit_id"].astype(str).isin(used_comment_ids)
    & compare_evidence["display_text"].astype(str).map(
        lambda value: comparison_brand_set <= _mentioned_brands(value)
    )
].sort_values(["display_priority", "comment_unit_id"])
cross_brand_markup = ""
if not cross_brand_rows.empty:
    cross_row = cross_brand_rows.iloc[0]
    used_comment_ids.add(str(cross_row["comment_unit_id"]))
    cross_brand_markup = _quote_card(cross_row, compact=True)
side_a = _comparison_side(
    brand_a, population_a, compare_evidence, selected_theme, used_comment_ids
)
side_b = _comparison_side(
    brand_b, population_b, compare_evidence, selected_theme, used_comment_ids
)
st.markdown(
    f'<div class="voc-compare-grid">{side_a}{side_b}</div>',
    unsafe_allow_html=True,
)

comparison_copy = _comparison_sentence(
    brand_a, brand_b, population_a, population_b, selected_theme
)
st.markdown(
    compact_html(
        f"""
        <div class="voc-comparison-takeaway"><span>What differs</span><strong>{escape(comparison_copy)}</strong>{cross_brand_markup}</div>
        """
    ),
    unsafe_allow_html=True,
)

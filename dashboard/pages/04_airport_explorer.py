"""Airport View - executive airport watchlist and same-location comparisons."""

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.executive_insights import validate_insights
from components.layout import render_page_header, render_section_heading
from utils.assets import brand_logo_img
from utils.constants import (
    DATA_DIR,
    ENTITY_COLORS,
    ENTITY_SHORT_NAMES,
    HEADLINE_ISSUERS,
)
from utils.data_loader import load_csv, load_presentation_dataset
from utils.html import compact_html
from utils.styling import apply_base_styles
from utils.validation import DataContractError, require_columns, require_unique


ROWS_FILE = DATA_DIR / "57_airport_view_brand_airport.csv"
BATTLEGROUNDS_FILE = DATA_DIR / "57_airport_view_battlegrounds.csv"
SUMMARY_FILE = DATA_DIR / "57_airport_view_summary.csv"
QA_FILE = DATA_DIR / "57_airport_view_qa.csv"
AIRPORT_STYLE_FILE = (
    Path(__file__).resolve().parents[1] / "assets" / "styles" / "airport_view.css"
)
BRAND_OPTIONS = ("ALL", *HEADLINE_ISSUERS)
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
AIRPORT_OVERVIEW_CARDS = {
    "AMEX": {
        "headline": (
            "Amex airport feedback shows concentrated access and capacity pressure."
        ),
        "what_stands_out": (
            "The strongest negative patterns cluster at specific airports rather "
            "than appearing uniformly."
        ),
        "examples": (
            {
                "airport_code": "LAX",
                "text": (
                    "clear negative pressure and a sharp same-airport contrast with "
                    "Delta."
                ),
                "evidence_id": "AMEX_LAX_01",
            },
            {
                "airport_code": "DFW",
                "text": "crowding is the clearest supported local capacity friction.",
                "evidence_id": "AMEX_DFW_02",
            },
            {
                "airport_code": "SLC",
                "text": "favorable feedback provides an important counterexample.",
            },
        ),
        "overall_read": (
            "Amex pressure is concentrated in local access and capacity issues."
        ),
        "supporting_insight_ids": (
            "AP_AMEX_01",
            "AP_AMEX_02",
            "AP_AMEX_03",
        ),
    },
    "CHASE": {
        "headline": (
            "Chase airport performance is mixed, with clear positive and negative pockets."
        ),
        "what_stands_out": (
            "Feedback varies materially by airport rather than leaning consistently "
            "in one direction."
        ),
        "examples": (
            {
                "airport_code": "LGA",
                "text": "the clearest positive airport pattern.",
                "evidence_id": "CHASE_LGA_02",
            },
            {
                "airport_code": "JFK",
                "text": "queue and wait-time friction contributes to negative feedback.",
            },
            {
                "airport_code": "LAS",
                "text": "negative feedback contrasts with Capital One.",
                "evidence_id": "CHASE_LAS_01",
            },
        ),
        "overall_read": "Chase's airport experience is highly location-dependent.",
        "supporting_insight_ids": (
            "AP_CHASE_01",
            "AP_CHASE_02",
            "AP_CHASE_03",
        ),
    },
    "CAPITAL_ONE": {
        "headline": "Capital One shows the broadest set of favorable airport-level signals.",
        "what_stands_out": (
            "Positive feedback spans several airports rather than relying on one "
            "standout."
        ),
        "examples": (
            {
                "airport_code": "JFK",
                "text": "a strong positive contrast with Amex and Chase.",
                "evidence_id": "CAPITAL_ONE_JFK_01",
            },
            {
                "airport_code": "LAS",
                "text": "favorable feedback versus Chase.",
            },
            {
                "airport_code": "DCA",
                "text": "food quality supports positive feedback.",
                "evidence_id": "CAPITAL_ONE_DCA_02",
            },
        ),
        "overall_read": (
            "Available evidence indicates a comparatively consistent positive "
            "experience across multiple airports."
        ),
        "supporting_insight_ids": (
            "AP_CAPITAL_ONE_01",
            "AP_CAPITAL_ONE_02",
            "AP_CAPITAL_ONE_03",
        ),
    },
    "DELTA": {
        "headline": "Delta's available airport evidence is limited but distinctly favorable.",
        "what_stands_out": (
            "Delta's strongest supported location signal is positive."
        ),
        "examples": (
            {
                "airport_code": "LAX",
                "text": (
                    "strong positive feedback and a clear same-airport contrast with "
                    "Amex."
                ),
                "evidence_id": "DELTA_LAX_01",
            },
        ),
        "overall_read": (
            "The signal is favorable, but narrow coverage keeps the conclusion "
            "location-specific."
        ),
        "supporting_insight_ids": ("AP_DELTA_01", "AP_DELTA_02"),
    },
}


apply_base_styles()
if AIRPORT_STYLE_FILE.is_file():
    st.html(f"<style>{AIRPORT_STYLE_FILE.read_text(encoding='utf-8')}</style>")


def _load_and_validate() -> tuple[pd.DataFrame, ...]:
    rows = load_csv(ROWS_FILE)
    battlegrounds = load_csv(BATTLEGROUNDS_FILE)
    summary = load_csv(SUMMARY_FILE)
    qa = load_csv(QA_FILE)
    insights = load_presentation_dataset("AIRPORT_DYNAMIC_INSIGHTS")
    insight_qa = load_presentation_dataset("AIRPORT_DYNAMIC_INSIGHT_QA")
    representative_comments = load_presentation_dataset(
        "AIRPORT_REPRESENTATIVE_COMMENTS"
    )
    representative_comment_qa = load_presentation_dataset(
        "AIRPORT_REPRESENTATIVE_COMMENT_QA"
    )
    count_columns = [
        "unique_comments",
        "positive_comments",
        "negative_comments",
        "mixed_neutral_comments",
    ]
    require_columns(
        rows,
        [
            "brand",
            "brand_display",
            "airport_code",
            "airport_name",
            "city",
            "state",
            "latitude",
            "longitude",
            "frozen_overall_score_100",
            "frozen_overall_comments",
            "frozen_attribute_score_100",
            "frozen_attribute_comments",
            "airport_unique_comments",
            "presentation_direction",
            *count_columns,
            "driver_label",
            "driver_theme",
            "driver_score_100",
            "watchlist_section",
            "watchlist_order",
        ],
        "AIRPORT_VIEW_BRAND_AIRPORT",
    )
    require_columns(
        battlegrounds,
        [
            "brand",
            "brand_display",
            "airport_code",
            "airport_name",
            *count_columns,
            "comparison_score_100",
            "same_airport_difference_pp",
            "sampled_competitor_count",
            "comparison_label",
            "comparison_takeaway",
        ],
        "AIRPORT_VIEW_BATTLEGROUNDS",
    )
    require_columns(summary, ["metric", "value"], "AIRPORT_VIEW_SUMMARY")
    require_columns(qa, ["check", "status"], "AIRPORT_VIEW_QA")
    require_unique(rows, ["brand", "airport_code"], "AIRPORT_VIEW_BRAND_AIRPORT")
    require_unique(summary, ["metric"], "AIRPORT_VIEW_SUMMARY")
    if not qa["status"].eq("PASS").all():
        failed = qa.loc[qa["status"].ne("PASS"), "check"].astype(str).tolist()
        raise DataContractError(f"Airport presentation QA failed: {', '.join(failed)}")
    validate_insights(insights, insight_qa)
    if tuple(AIRPORT_OVERVIEW_CARDS) != HEADLINE_ISSUERS:
        raise DataContractError(
            "Airport overview cards must preserve the approved four-brand order"
        )
    require_columns(
        representative_comments,
        [
            "page",
            "dropdown_brand",
            "evidence_id",
            "comment_unit_id",
            "airport_code",
            "sentiment_group",
            "excerpt",
            "post_url",
            "source_mart",
            "display_order",
        ],
        "AIRPORT_REPRESENTATIVE_COMMENTS",
    )
    require_columns(
        representative_comment_qa,
        [
            "evidence_id",
            "dropdown_brand",
            "brand_match",
            "airport_insight_match",
            "public_safe",
            "url_valid",
            "status",
        ],
        "AIRPORT_REPRESENTATIVE_COMMENT_QA",
    )
    require_unique(
        representative_comments,
        ["evidence_id"],
        "AIRPORT_REPRESENTATIVE_COMMENTS",
    )
    require_unique(
        representative_comment_qa,
        ["evidence_id"],
        "AIRPORT_REPRESENTATIVE_COMMENT_QA",
    )
    if not representative_comment_qa["status"].eq("PASS").all():
        failed = representative_comment_qa.loc[
            representative_comment_qa["status"].ne("PASS"), "evidence_id"
        ].astype(str).tolist()
        raise DataContractError(
            f"Airport representative-comment QA failed: {', '.join(failed)}"
        )
    qa_flags = ("brand_match", "airport_insight_match", "public_safe", "url_valid")
    if not all(
        representative_comment_qa[column].astype(str).str.upper().eq("TRUE").all()
        for column in qa_flags
    ):
        raise DataContractError(
            "Airport representative comments must pass every evidence-quality check"
        )
    if set(representative_comments["evidence_id"]) != set(
        representative_comment_qa["evidence_id"]
    ):
        raise DataContractError(
            "Airport representative comments and their QA rows must match exactly"
        )
    expected_counts = {brand: 2 for brand in HEADLINE_ISSUERS}
    actual_counts = (
        representative_comments.groupby("dropdown_brand")["evidence_id"]
        .count()
        .to_dict()
    )
    if actual_counts != expected_counts:
        raise DataContractError(
            "Airport representative comments must contain exactly two rows per named brand"
        )
    if not representative_comments["post_url"].astype(str).str.startswith(
        "https://www.reddit.com/"
    ).all():
        raise DataContractError(
            "Airport representative comments must use public Reddit post links"
        )
    for brand, card in AIRPORT_OVERVIEW_CARDS.items():
        examples = tuple(card["examples"])
        if not 1 <= len(examples) <= 3:
            raise DataContractError(
                f"Airport overview for {brand} must use one to three airport examples"
            )
        source_count = sum(bool(example.get("evidence_id")) for example in examples)
        if source_count > 2:
            raise DataContractError(
                f"Airport overview for {brand} cannot use more than two source links"
            )
        for insight_id in card["supporting_insight_ids"]:
            supporting_rows = insights.loc[
                insights["insight_id"].eq(insight_id)
                & insights["dropdown_brand"].eq(brand)
            ]
            if len(supporting_rows) != 1 or not supporting_rows[
                "evidence_threshold_pass"
            ].astype(str).str.upper().eq("TRUE").all():
                raise DataContractError(
                    f"Airport overview for {brand} lacks approved support: {insight_id}"
                )
        for example in examples:
            evidence_id = example.get("evidence_id", "")
            if not evidence_id:
                continue
            evidence_rows = representative_comments.loc[
                representative_comments["evidence_id"].eq(evidence_id)
                & representative_comments["dropdown_brand"].eq(brand)
                & representative_comments["airport_code"].eq(
                    str(example["airport_code"])
                )
            ]
            if len(evidence_rows) != 1:
                raise DataContractError(
                    f"Airport overview source {evidence_id} does not match {brand} "
                    f"at {example['airport_code']}"
                )
    return (
        rows,
        battlegrounds,
        summary,
        qa,
        insights,
        insight_qa,
        representative_comments,
        representative_comment_qa,
    )


def _brand_label(value: str) -> str:
    return "All brands" if value == "ALL" else ENTITY_SHORT_NAMES.get(value, value)


def _summary_value(summary: pd.DataFrame, metric: str) -> int:
    matches = summary.loc[summary["metric"].eq(metric), "value"]
    if len(matches) != 1:
        raise DataContractError(f"Airport summary must contain one row for {metric}")
    return int(matches.iloc[0])


def _safe_text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def _render_airport_overview(comments: pd.DataFrame) -> int:
    """Render the fixed four-brand airport story above the detailed filter."""
    cards: list[str] = []
    for brand in HEADLINE_ISSUERS:
        display = AIRPORT_OVERVIEW_CARDS[brand]
        examples: list[str] = []
        for example in display["examples"]:
            evidence_id = example.get("evidence_id", "")
            source_markup = ""
            if evidence_id:
                evidence = comments.loc[
                    comments["evidence_id"].eq(evidence_id)
                ].iloc[0]
                airport_code = str(example["airport_code"])
                source_markup = (
                    f'<a class="exec-brand-source airport-overview-source" '
                    f'href="{escape(str(evidence["post_url"]))}" target="_blank" '
                    f'rel="noopener noreferrer">See representative '
                    f'{escape(airport_code)} comment&nbsp;'
                    '<span aria-hidden="true">↗</span></a>'
                )
            examples.append(
                compact_html(
                    f"""
                    <li>
                        <div><strong>{escape(str(example['airport_code']))}:</strong>
                        <span>{escape(str(example['text']))}</span></div>
                        {source_markup}
                    </li>
                    """
                )
            )
        color = ENTITY_COLORS.get(brand, "#3468d4")
        cards.append(
            compact_html(
                f"""
                <article class="exec-brand-card airport-overview-card" style="--brand-color:{color}">
                    <div class="exec-brand-mark">{brand_logo_img(brand)}<span>{escape(ENTITY_SHORT_NAMES[brand])}</span></div>
                    <div class="exec-brand-headline">{escape(str(display['headline']))}</div>
                    <div class="exec-brand-interpretation">
                        <div class="exec-brand-signal airport-overview-standout">
                            <span>What stands out</span>
                            <strong>{escape(str(display['what_stands_out']))}</strong>
                        </div>
                        <div class="exec-brand-signal airport-overview-locations">
                            <span>Where it shows up</span>
                            <ul>{''.join(examples)}</ul>
                        </div>
                    </div>
                    <div class="airport-overview-read">
                        <span>Overall takeaway</span>
                        <strong>{escape(str(display['overall_read']))}</strong>
                    </div>
                </article>
                """
            )
        )
    st.markdown(
        f'<div class="exec-brand-grid airport-overview-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )
    return len(cards)


def _sentiment_bar(row: pd.Series, compact: bool = False) -> str:
    total = max(int(row["unique_comments"]), 1)
    positive = int(row["positive_comments"])
    negative = int(row["negative_comments"])
    mixed = int(row["mixed_neutral_comments"])
    size_class = " compact" if compact else ""
    return compact_html(
        f"""
        <div class="exec-sentiment-bar{size_class}" aria-label="{positive} positive, {negative} negative, {mixed} mixed or neutral comments">
            <i class="positive" style="width:{positive / total * 100:.3f}%" title="{positive} positive"></i>
            <i class="negative" style="width:{negative / total * 100:.3f}%" title="{negative} negative"></i>
            <i class="mixed" style="width:{mixed / total * 100:.3f}%" title="{mixed} mixed or neutral"></i>
        </div>
        """
    )


def _count_line(row: pd.Series) -> str:
    return (
        f"{int(row['positive_comments'])} positive / "
        f"{int(row['negative_comments'])} negative / "
        f"{int(row['mixed_neutral_comments'])} mixed/neutral"
    )


def _filter_rows(rows: pd.DataFrame, brand: str) -> pd.DataFrame:
    if brand == "ALL":
        return rows.copy()
    return rows.loc[rows["brand"].eq(brand)].copy()


def _snapshot(rows: pd.DataFrame, battlegrounds: pd.DataFrame, brand: str) -> None:
    current = _filter_rows(rows, brand)
    if brand == "ALL":
        competitive_airports = battlegrounds["airport_code"].nunique()
    else:
        competitive_airports = battlegrounds.loc[
            battlegrounds["brand"].eq(brand), "airport_code"
        ].nunique()
    facts = (
        (
            current["airport_code"].nunique(),
            "airports with sufficient location-specific evidence",
        ),
        (
            competitive_airports,
            "airports with enough same-location evidence for brand comparison",
        ),
        (
            current["brand"].nunique(),
            "headline brands represented" if brand == "ALL" else "selected brand",
        ),
    )
    cards = "".join(
        f'<div class="airport-exec-fact"><strong>{value}</strong><span>{escape(label)}</span></div>'
        for value, label in facts
    )
    st.markdown(
        f'<div class="airport-exec-summary">{cards}</div>', unsafe_allow_html=True
    )


def _render_all_airports(
    rows: pd.DataFrame, battlegrounds: pd.DataFrame, brand: str
) -> int:
    current = _filter_rows(rows, brand).sort_values(["airport_code", "brand_order"])
    comparison_rows = (
        battlegrounds
        if brand == "ALL"
        else battlegrounds.loc[battlegrounds["brand"].eq(brand)]
    )
    competitive_airports = set(comparison_rows["airport_code"].astype(str))
    table_rows: list[str] = []
    for airport, group in current.groupby("airport_code", sort=True):
        first = group.iloc[0]
        brand_names = ", ".join(group["brand_display"].astype(str))
        brand_count = group["brand"].nunique()
        brand_support = (
            f"{brand_count} brands" if brand_count > 1 else "1 brand"
        )
        composition_items = []
        show_brand_prefix = brand == "ALL" and brand_count > 1
        for _, row in group.iterrows():
            brand_prefix = (
                f'<b>{escape(str(row["brand_display"]))}:</b> '
                if show_brand_prefix
                else ""
            )
            composition_items.append(
                compact_html(
                    f"""
                    <span>{brand_prefix}<em class="positive">{int(row['positive_comments'])} positive</em><i>&middot;</i><em class="negative">{int(row['negative_comments'])} negative</em><i>&middot;</i><em class="mixed">{int(row['mixed_neutral_comments'])} mixed</em></span>
                    """
                )
            )
        drivers = []
        for _, row in group.loc[group["driver_label"].notna()].iterrows():
            driver_score = pd.to_numeric(row.get("driver_score_100"), errors="coerce")
            if pd.isna(driver_score):
                direction_label, direction_class = "Unclear", "neutral"
            elif float(driver_score) > 0:
                direction_label, direction_class = "Positive", "positive"
            elif float(driver_score) < 0:
                direction_label, direction_class = "Negative", "negative"
            else:
                direction_label, direction_class = "Mixed", "neutral"
            drivers.append(
                f'<span><b>{escape(str(row["brand_display"]))}:</b> '
                f'{escape(str(row["driver_label"]))} '
                f'<em class="airport-exec-driver-direction {direction_class}">&middot; {direction_label}</em></span>'
            )
        driver_markup = "".join(drivers) or (
            '<span class="muted airport-exec-no-driver" '
            'title="No sufficiently supported experience driver.">—</span>'
        )
        if brand == "ALL":
            comment_count = int(first["airport_unique_comments"])
            comment_label = "comments"
        else:
            comment_count = int(first["unique_comments"])
            comment_label = "comments"
        competitive = airport in competitive_airports
        comparison_markup = (
            '<span class="airport-exec-yes">Yes</span>'
            if competitive
            else '<span class="airport-exec-no">No</span>'
        )
        table_rows.append(
            compact_html(
                f"""
                <div class="airport-exec-table-row">
                    <div class="airport-exec-airport-cell"><strong>{escape(str(airport))}</strong><span>{escape(str(first['airport_name']))}</span><small>{escape(str(first['city']))}, {escape(str(first['state']))}</small></div>
                    <div class="airport-exec-brands-cell"><strong>{escape(brand_names)}</strong><span>{escape(brand_support)}</span></div>
                    <div class="airport-exec-comments-cell"><div class="airport-exec-comment-total"><strong>{comment_count}</strong><small>{comment_label}</small></div><div class="airport-exec-composition">{"".join(composition_items)}</div></div>
                    <div class="airport-exec-signal-cell">{driver_markup}</div>
                    <div class="airport-exec-compare-cell">{comparison_markup}</div>
                </div>
                """
            )
        )
    header = compact_html(
        """
        <div class="airport-exec-table-head">
            <span>Airport</span><span>Brands with evidence</span><span>Comments & feedback</span>
            <span>Primary experience driver</span><span>Comparison</span>
        </div>
        """
    )
    st.markdown(
        f'<div class="airport-exec-all-table">{header}{"".join(table_rows)}</div>',
        unsafe_allow_html=True,
    )
    return len(table_rows)


def _driver_context(row: pd.Series) -> str:
    theme = _safe_text(row.get("driver_theme"))
    driver = _safe_text(row.get("driver_label"))
    return f"{driver} ({theme})" if theme and driver else driver


def _watchlist_insight(row: pd.Series, section: str) -> str:
    driver = _safe_text(row.get("driver_label"))
    driver_score = pd.to_numeric(row.get("driver_score_100"), errors="coerce")
    brand = str(row["brand_display"])
    if section == "ATTENTION":
        if driver and pd.notna(driver_score) and float(driver_score) < 0:
            return (
                f"{driver} and overall lounge feedback are negative in the "
                f"available {brand} sample."
            )
        return f"Overall lounge feedback is negative in the available {brand} sample."
    if driver and pd.notna(driver_score) and float(driver_score) > 0:
        return (
            f"{driver} and overall lounge feedback stand out positively in the "
            f"available {brand} sample."
        )
    return f"Overall lounge feedback stands out positively in the available {brand} sample."


def _watchlist_card(row: pd.Series, section: str) -> str:
    tone = "negative" if section == "ATTENTION" else "positive"
    driver = _safe_text(row.get("driver_label"))
    theme = _safe_text(row.get("driver_theme"))
    driver_heading = "Main issue" if section == "ATTENTION" else "Supported positive driver"
    driver_markup = (
        f'<div class="airport-exec-driver"><span>{escape(driver_heading)}</span><strong>{escape(driver)}</strong><small>{escape(theme)}</small></div>'
        if driver
        and pd.notna(pd.to_numeric(row.get("driver_score_100"), errors="coerce"))
        and (
            (section == "ATTENTION" and float(row["driver_score_100"]) < 0)
            or (section == "POSITIVE" and float(row["driver_score_100"]) > 0)
        )
        else ""
    )
    tooltip = (
        f"{int(row['positive_comments'])} positive, "
        f"{int(row['negative_comments'])} negative and "
        f"{int(row['mixed_neutral_comments'])} mixed or neutral comments."
    )
    location = f"{row['city']}, {row['state']}"
    return compact_html(
        f"""
        <article class="airport-exec-watch-card {tone}" title="{escape(tooltip)}">
            <div class="airport-exec-card-top">
                <div><strong>{escape(str(row['airport_code']))}</strong><span>{escape(str(row['airport_name']))}</span></div>
                <b>{escape(str(row['brand_display']))}</b>
            </div>
            <div class="airport-exec-location">{escape(location)}</div>
            <div class="airport-exec-volume"><strong>{int(row['unique_comments'])}</strong><span>qualifying comments</span></div>
            {_sentiment_bar(row)}
            <div class="exec-count-line">{escape(_count_line(row))}</div>
            {driver_markup}
            <p>{escape(_watchlist_insight(row, section))}</p>
        </article>
        """
    )


def _render_watchlist(rows: pd.DataFrame, brand: str, section: str) -> int:
    selected = _filter_rows(rows, brand)
    selected = selected.loc[selected["watchlist_section"].eq(section)].sort_values(
        "watchlist_order"
    ).head(4)
    if selected.empty:
        st.markdown(
            compact_html(
                f"""
                <div class="airport-exec-empty">
                    No sufficiently supported {'negative' if section == 'ATTENTION' else 'positive'} watchlist signal is available for {escape(_brand_label(brand))}.
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
        return 0
    cards = "".join(
        _watchlist_card(row, section) for _, row in selected.iterrows()
    )
    st.markdown(
        f'<div class="airport-exec-watch-grid">{cards}</div>', unsafe_allow_html=True
    )
    return len(selected)


def _battle_row(row: pd.Series, selected_brand: str) -> str:
    selected_class = " selected" if selected_brand == str(row["brand"]) else ""
    tooltip = (
        f"{int(row['positive_comments'])} positive, "
        f"{int(row['negative_comments'])} negative and "
        f"{int(row['mixed_neutral_comments'])} mixed or neutral comments."
    )
    return compact_html(
        f"""
        <div class="airport-exec-battle-row{selected_class}" title="{escape(tooltip)}">
            <div class="airport-exec-battle-brand"><strong>{escape(str(row['brand_display']))}</strong><span>{int(row['unique_comments'])} qualifying comments</span></div>
            <div>
                {_sentiment_bar(row, compact=True)}
                <div class="exec-count-line compact">{escape(_count_line(row))}</div>
            </div>
        </div>
        """
    )


def _render_battlegrounds(
    battlegrounds: pd.DataFrame, selected_brand: str
) -> int:
    if selected_brand == "ALL":
        ranking = (
            battlegrounds.assign(
                comparison_magnitude=pd.to_numeric(
                    battlegrounds["same_airport_difference_pp"], errors="coerce"
                ).abs()
            )
            .groupby("airport_code")["comparison_magnitude"]
            .max()
            .sort_values(ascending=False)
        )
    else:
        ranking = (
            battlegrounds.loc[battlegrounds["brand"].eq(selected_brand)]
            .assign(
                comparison_magnitude=lambda frame: pd.to_numeric(
                    frame["same_airport_difference_pp"], errors="coerce"
                ).abs()
            )
            .set_index("airport_code")["comparison_magnitude"]
            .sort_values(ascending=False)
        )
    airport_codes = ranking.head(4).index.astype(str).tolist()
    cards = []
    for airport in airport_codes:
        group = battlegrounds.loc[battlegrounds["airport_code"].eq(airport)].sort_values(
            "comparison_score_100", ascending=False
        )
        if group.empty:
            continue
        first = group.iloc[0]
        if selected_brand == "ALL":
            peer_count = int(group["brand"].nunique()) - 1
        else:
            peer_count = int(
                group.loc[group["brand"].eq(selected_brand), "sampled_competitor_count"].iloc[0]
            )
        label = (
            "Head-to-head"
            if peer_count == 1
            else "Multi-brand comparison"
        )
        supporting = (
            "Two brands have enough same-location evidence."
            if peer_count == 1
            else f"{group['brand'].nunique()} brands have enough same-location evidence."
        )
        rows_markup = "".join(
            _battle_row(row, selected_brand) for _, row in group.iterrows()
        )
        cards.append(
            compact_html(
                f"""
                <article class="airport-exec-battle-card">
                    <div class="airport-exec-battle-top">
                        <div><strong>{escape(airport)}</strong><span>{escape(str(first['airport_name']))}</span></div>
                        <b>{escape(label)}</b>
                    </div>
                    <small>{escape(supporting)}</small>
                    <div class="airport-exec-battle-rows">{rows_markup}</div>
                    <p>{escape(str(first['comparison_takeaway']))}</p>
                </article>
                """
            )
        )
    if not cards:
        st.markdown(
            f'<div class="airport-exec-empty">No same-airport comparison is available for {escape(_brand_label(selected_brand))}.</div>',
            unsafe_allow_html=True,
        )
        return 0
    st.markdown(
        f'<div class="airport-exec-battle-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )
    return len(cards)


def _map_direction(group: pd.DataFrame, brand: str) -> str:
    if brand == "ALL":
        return "supported"
    watchlist_section = str(group.iloc[0].get("watchlist_section", ""))
    return {"POSITIVE": "positive", "ATTENTION": "negative"}.get(
        watchlist_section, "supported"
    )


def _map_classification_label(direction: str) -> str:
    return {
        "positive": "Performing well",
        "negative": "Needs attention",
        "supported": "Supported / mixed",
    }[direction]


def _bounded_marker_sizes(comment_counts: pd.Series) -> pd.Series:
    """Keep every airport tappable without letting the largest sample dominate."""
    rooted = np.sqrt(pd.to_numeric(comment_counts, errors="coerce").fillna(0).clip(0))
    low = float(rooted.min())
    high = float(rooted.max())
    if high <= low:
        return pd.Series(19.0, index=comment_counts.index)
    return 13.0 + ((rooted - low) / (high - low)) * 13.0


def _map_figure(
    rows: pd.DataFrame, brand: str, competitive_airports: set[str]
) -> go.Figure:
    colors = {
        "positive": "#168461",
        "negative": "#c9474f",
        "supported": "#8995a7",
    }
    points: list[dict[str, object]] = []
    for airport, group in rows.groupby("airport_code"):
        group = group.sort_values("brand_order")
        first = group.iloc[0]
        direction = _map_direction(group, brand)
        has_comparison = airport in competitive_airports
        if brand == "ALL":
            brand_count = int(group["brand"].nunique())
            brand_lines = "<br>".join(
                f"{escape(str(row['brand_display']))} · {int(row['unique_comments'])} comments"
                for _, row in group.iterrows()
            )
            marker_comments = int(first["airport_unique_comments"])
            comparison_label = (
                "Direct comparison available"
                if has_comparison
                else "No direct comparison"
            )
            hover = (
                f"<b>{escape(str(airport))} · {escape(str(first['airport_name']))}</b><br>"
                f"Brands with evidence: {brand_count}<br>"
                f"Total qualifying comments shown: {marker_comments}<br><br>"
                f"{brand_lines}<br>"
                f"Comparison: {comparison_label}"
            )
        else:
            marker_comments = int(first["unique_comments"])
            driver = _safe_text(first.get("driver_label"))
            driver_score = pd.to_numeric(first.get("driver_score_100"), errors="coerce")
            driver_line = ""
            if driver and pd.notna(driver_score) and float(driver_score) != 0:
                driver_direction = "Positive" if float(driver_score) > 0 else "Negative"
                driver_line = (
                    f"<br>Primary experience driver: "
                    f"{escape(driver)} · {driver_direction}"
                )
            hover = (
                f"<b>{escape(str(airport))} · {escape(str(first['airport_name']))}</b><br>"
                f"Brand: {escape(str(first['brand_display']))}<br>"
                f"Evidence: {marker_comments} qualifying comments<br>"
                f"Feedback mix: {int(first['positive_comments'])} positive · "
                f"{int(first['negative_comments'])} negative · "
                f"{int(first['mixed_neutral_comments'])} mixed/neutral"
                f"{driver_line}<br>"
                f"Classification: {_map_classification_label(direction)}"
            )
        points.append(
            {
                "airport_code": airport,
                "latitude": float(first["latitude"]),
                "longitude": float(first["longitude"]),
                "direction": direction,
                "color": colors[direction],
                "comments": marker_comments,
                "comparison": has_comparison,
                "hover": hover,
            }
        )
    points_frame = pd.DataFrame(points)
    points_frame["size"] = _bounded_marker_sizes(points_frame["comments"])
    if brand == "ALL":
        points_frame["map_group"] = np.where(
            points_frame["comparison"], "comparison", "supported"
        )
    else:
        points_frame["map_group"] = points_frame["direction"]

    figure = go.Figure()
    groups = (
        ("supported", "comparison")
        if brand == "ALL"
        else ("negative", "supported", "positive")
    )
    for map_group in groups:
        subset = points_frame.loc[points_frame["map_group"].eq(map_group)]
        if subset.empty:
            continue
        if brand == "ALL":
            line_color = "#2f73b8" if map_group == "comparison" else "#ffffff"
            line_width = 3 if map_group == "comparison" else 1.5
            labels = (
                subset["airport_code"]
                if map_group == "comparison"
                else [""] * len(subset)
            )
        else:
            line_color = "#ffffff"
            line_width = 1.5
            labels = (
                subset["airport_code"]
                if map_group in {"negative", "positive"}
                else [""] * len(subset)
            )
        halo_color = (
            "#2f73b8"
            if brand == "ALL" and map_group == "comparison"
            else subset["color"]
        )
        figure.add_trace(
            go.Scattergeo(
                lon=subset["longitude"],
                lat=subset["latitude"],
                mode="markers",
                hoverinfo="skip",
                marker={
                    "size": subset["size"] + 9,
                    "color": halo_color,
                    "line": {"width": 0},
                    "opacity": 0.12,
                },
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scattergeo(
                lon=subset["longitude"],
                lat=subset["latitude"],
                text=labels,
                hovertext=subset["hover"],
                hovertemplate="%{hovertext}<extra></extra>",
                mode="markers+text",
                textposition="top center",
                textfont={
                    "size": 10,
                    "color": "#30445f",
                    "family": "Inter, Segoe UI, sans-serif",
                },
                marker={
                    "size": subset["size"],
                    "color": subset["color"],
                    "line": {"color": line_color, "width": line_width},
                    "opacity": 0.94 if map_group != "supported" else 0.86,
                },
                name=map_group.title(),
            )
        )
    figure.update_geos(
        scope="usa",
        projection_type="albers usa",
        showland=True,
        landcolor="#e8eef5",
        showocean=True,
        oceancolor="#f6f9fd",
        showlakes=True,
        lakecolor="#dfeaf5",
        showsubunits=True,
        subunitcolor="#cbd6e3",
        subunitwidth=0.7,
        showcoastlines=True,
        coastlinecolor="#b9c8d9",
        coastlinewidth=0.9,
        countrycolor="#afbed0",
        countrywidth=1,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
    )
    figure.update_layout(
        height=430,
        margin={"l": 0, "r": 0, "t": 6, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font={"family": "Inter, Segoe UI, sans-serif", "color": "#26334b"},
        hoverlabel={
            "bgcolor": "#ffffff",
            "bordercolor": "#cbd5e1",
            "font": {"size": 12, "color": "#24324a"},
            "align": "left",
        },
    )
    return figure


try:
    (
        airport_rows,
        battleground_rows,
        airport_summary,
        airport_qa,
        insights,
        insight_qa,
        representative_comments,
        representative_comment_qa,
    ) = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"Airport View cannot load its presentation data. {error}")
    st.stop()

render_page_header(
    "Airport View",
    "See where lounge feedback stands out across US airports and where brands can be compared at the same location.",
)

render_section_heading(
    "Airport Overview",
    "The clearest location-level experience patterns across Amex, Chase, Capital One and Delta.",
)
_render_airport_overview(representative_comments)

render_section_heading(
    "Explore Airports by Brand",
    "Select a brand to explore its airport-level feedback in more detail.",
)
selected_brand = st.selectbox(
    "Brand",
    BRAND_OPTIONS,
    index=0,
    format_func=_brand_label,
    key="airport_view_brand",
)

st.markdown(
    compact_html(
        """
        <div class="airport-exec-scope-note">
            <strong>Only airports with enough location-specific feedback are included.</strong>
            Missing airports do not indicate neutral performance or the absence of a lounge.
        </div>
        """
    ),
    unsafe_allow_html=True,
)

render_section_heading(
    "Airport-Level Performance",
    "Detailed location-level feedback for the selected brand view.",
)
all_airports_count = _render_all_airports(
    airport_rows, battleground_rows, selected_brand
)

render_section_heading(
    "Airports needing attention",
    "The strongest sufficiently supported negative airport signals in the available Reddit feedback.",
)
negative_count = _render_watchlist(airport_rows, selected_brand, "ATTENTION")

render_section_heading(
    "Airports performing well",
    "Locations where sufficiently supported lounge feedback is especially positive.",
)
positive_count = _render_watchlist(airport_rows, selected_brand, "POSITIVE")

render_section_heading(
    "Where brands can be compared directly",
    "Airports with enough same-location evidence to support a brand comparison.",
)
battleground_count = _render_battlegrounds(battleground_rows, selected_brand)

render_section_heading(
    "Airport Signal Map",
    "A geographic view of where the strongest supported airport experience signals appear.",
)
map_rows = _filter_rows(airport_rows, selected_brand)
if selected_brand == "ALL":
    map_competitive_airports = set(battleground_rows["airport_code"].astype(str))
else:
    map_competitive_airports = set(
        battleground_rows.loc[
            battleground_rows["brand"].eq(selected_brand), "airport_code"
        ].astype(str)
    )
if selected_brand == "ALL":
    map_legend = '<span><i class="supported"></i> Supported airport</span><span><i class="comparison"></i> Direct comparison available</span><span><i class="volume"></i> Marker size = evidence volume</span>'
else:
    map_legend = '<span><i class="negative"></i> Needs attention</span><span><i class="positive"></i> Performing well</span><span><i class="supported"></i> Other supported airport</span><span><i class="volume"></i> Marker size = evidence volume</span>'
st.markdown(
    f'<div class="airport-exec-map-legend">{map_legend}</div>',
    unsafe_allow_html=True,
)
with st.container(border=True, key="airport-exec-map-panel"):
    st.plotly_chart(
        _map_figure(map_rows, selected_brand, map_competitive_airports),
        width="stretch",
        config=PLOT_CONFIG,
        theme=None,
    )
st.markdown(
    '<div class="airport-exec-map-note">All Brands remains neutral because no combined brand sentiment is calculated. Select a brand to see the same experience classifications used in the airport cards above.</div>',
    unsafe_allow_html=True,
)

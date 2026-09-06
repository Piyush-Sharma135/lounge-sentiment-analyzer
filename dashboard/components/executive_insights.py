"""Reusable rendering and validation for frozen executive insight records."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.icons import icon_svg
from utils.constants import ENTITY_SHORT_NAMES
from utils.html import compact_html
from utils.validation import DataContractError, require_columns, require_unique


INSIGHT_COLUMNS = (
    "page",
    "section",
    "insight_id",
    "headline",
    "evidence_text",
    "implication_text",
    "implication_type",
    "source_mart",
    "evidence_threshold_pass",
    "display_order",
)


def validate_insights(insights: pd.DataFrame, qa: pd.DataFrame) -> None:
    """Require a passing, one-to-one QA record for every displayed insight."""
    require_columns(insights, list(INSIGHT_COLUMNS), "EXECUTIVE_INSIGHTS")
    statement_column = "displayed_statement" if "displayed_statement" in qa.columns else "insight"
    require_columns(
        qa,
        ["page", "section", "insight_id", statement_column, "status"],
        "EXECUTIVE_INSIGHT_QA",
    )
    require_unique(insights, ["insight_id"], "EXECUTIVE_INSIGHTS")
    require_unique(qa, ["insight_id"], "EXECUTIVE_INSIGHT_QA")
    insight_ids = set(insights["insight_id"].astype(str))
    qa_ids = set(qa["insight_id"].astype(str))
    if insight_ids != qa_ids:
        raise DataContractError("Executive insight and QA records do not match one-to-one")
    if not insights["evidence_threshold_pass"].astype(str).str.upper().eq("TRUE").all():
        raise DataContractError("An executive insight did not pass its evidence threshold")
    if not qa["status"].astype(str).str.upper().eq("PASS").all():
        raise DataContractError("An executive insight QA record is not PASS")
    statements = qa.set_index("insight_id")[statement_column].astype(str)
    headlines = insights.set_index("insight_id")["headline"].astype(str)
    if not headlines.sort_index().equals(statements.sort_index()):
        raise DataContractError("Executive insight headlines do not match their QA records")


def render_insights(
    insights: pd.DataFrame,
    *,
    page: str,
    section: str,
    dropdown_brand: str | None = None,
) -> int:
    """Render the ordered frozen insight records for one page section."""
    selected = insights.loc[
        insights["page"].eq(page) & insights["section"].eq(section)
    ].copy()
    if dropdown_brand is not None:
        if "dropdown_brand" not in selected.columns:
            raise DataContractError("Dynamic insights require dropdown_brand")
        selected = selected.loc[selected["dropdown_brand"].eq(dropdown_brand)]
    selected = selected.sort_values("display_order")
    is_brand_comparison = page == "Executive Overview" and section == "Brand-level signals"
    cards = []
    for _, row in selected.iterrows():
        brand = str(row.get("primary_brand", ""))
        brand_class = (
            f" brand-{brand.lower().replace('_', '-')}"
            if is_brand_comparison and brand
            else ""
        )
        label = ENTITY_SHORT_NAMES.get(brand, brand)
        label_markup = (
            f'<div class="leadership-insight-label">{escape(label)}</div>'
            if is_brand_comparison and label
            else ""
        )
        headline = str(row["headline"])
        if section == "Trend insights":
            icon_name = "trend"
        elif "crowding" in headline.lower() or "access" in headline.lower():
            icon_name = "capacity"
        elif "food" in headline.lower() or "beverage" in headline.lower():
            icon_name = "food"
        elif "space" in headline.lower() or "convenience" in headline.lower():
            icon_name = "amenities"
        else:
            icon_name = "drivers"
        insight_icon = icon_svg(icon_name, css_class="leadership-insight-icon")
        if is_brand_comparison:
            pressure_text = row.get("pressure_text")
            if pd.isna(pressure_text) or not str(pressure_text).strip():
                raise DataContractError("Brand insights require a pressure_text value")
            body_markup = compact_html(
                f"""
                <ul class="leadership-insight-bullets">
                    <li class="positive-signal">
                        <strong>Positive signal</strong>
                        <span>{escape(str(row['evidence_text']))}</span>
                    </li>
                    <li class="pressure-signal">
                        <strong>Pressure signal</strong>
                        <span>{escape(str(pressure_text))}</span>
                    </li>
                    <li class="overall-read">
                        <strong>Overall read</strong>
                        <span>{escape(str(row['implication_text']))}</span>
                    </li>
                </ul>
                """
            )
        else:
            body_markup = compact_html(
                f"""
                <p class="leadership-insight-evidence">{escape(str(row['evidence_text']))}</p>
                <p class="leadership-insight-action">{escape(str(row['implication_text']))}</p>
                """
            )
        cards.append(
            compact_html(
                f"""
                <article class="leadership-insight-card{brand_class}">
                    {insight_icon}
                    {label_markup}
                    <h3>{escape(headline)}</h3>
                    {body_markup}
                </article>
                """
            )
        )
    if cards:
        grid_class = "leadership-insight-grid brand-comparison" if is_brand_comparison else "leadership-insight-grid"
        st.markdown(
            f'<div class="{grid_class}">{"".join(cards)}</div>',
            unsafe_allow_html=True,
        )
    return len(cards)

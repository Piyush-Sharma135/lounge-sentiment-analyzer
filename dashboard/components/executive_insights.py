"""Reusable rendering and validation for frozen executive insight records."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

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
    cards = []
    for _, row in selected.iterrows():
        cards.append(
            compact_html(
                f"""
                <article class="leadership-insight-card">
                    <h3>{escape(str(row['headline']))}</h3>
                    <p class="leadership-insight-evidence">{escape(str(row['evidence_text']))}</p>
                    <p class="leadership-insight-action">{escape(str(row['implication_text']))}</p>
                </article>
                """
            )
        )
    if cards:
        st.markdown(
            f'<div class="leadership-insight-grid">{"".join(cards)}</div>',
            unsafe_allow_html=True,
        )
    return len(cards)

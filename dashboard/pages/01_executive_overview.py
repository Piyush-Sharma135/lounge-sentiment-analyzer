"""Executive Overview — a concise national lounge-experience summary."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.executive_insights import render_insights, validate_insights
from components.icons import theme_icon_svg
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


THEMES = (
    "General Lounge Experience",
    "Access & Capacity",
    "Food & Beverage",
    "Service & Upkeep",
    "Space, Amenities & Convenience",
)
THEME_SUBTHEMES = {
    "General Lounge Experience": "Overall impression of the lounge experience",
    "Access & Capacity": "Crowding · Wait time & queues · Seating · Access · Reservations",
    "Food & Beverage": "Food quality · Food availability · Beverage & bar",
    "Service & Upkeep": "Staff & service · Cleanliness",
    "Space, Amenities & Convenience": "Ambience · Amenities · Wi-Fi/workspace · Family/children · Location · Hours · Value",
}
OPERATIONAL_THEMES = (
    "Access & Capacity",
    "Food & Beverage",
    "Service & Upkeep",
    "Space, Amenities & Convenience",
)
MONTH_LABELS = {
    f"2026-{month:02d}": label
    for month, label in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"), start=1
    )
}
ASPECT_LABELS = {
    "CROWDING": "Crowding",
    "WAIT_TIME_QUEUE": "Wait time & queues",
    "SEATING_AVAILABILITY": "Seating availability",
    "ACCESS_EXPERIENCE": "Access experience",
    "RESERVATION_SYSTEM": "Reservation experience",
    "FOOD_QUALITY": "Food quality",
    "FOOD_AVAILABILITY": "Food availability",
    "BEVERAGE_BAR": "Beverage & bar",
    "STAFF_SERVICE": "Staff & service",
    "CLEANLINESS": "Cleanliness",
    "AMBIENCE_DESIGN": "Ambience & design",
    "AMENITIES": "Amenities",
    "WIFI_WORKSPACE": "Wi-Fi & workspace",
    "FAMILY_CHILDREN": "Family & children",
    "LOCATION_CONVENIENCE": "Location convenience",
    "OPERATING_HOURS": "Operating hours",
    "VALUE_FOR_MONEY": "Value for money",
}
BRAND_EVIDENCE_FILE = DATA_DIR / "58_voc_display_public.csv"
DISPLAY_IMPLICATION_OVERRIDES = {
    "EX_THEME_02": (
        "For Amex, food and beverage provides a meaningful positive counterweight "
        "to the more negative access and capacity pattern."
    ),
    "EX_THEME_03": (
        "For Amex, the weakness appears broad across this theme rather than "
        "attributable to one sufficiently supported experience driver."
    ),
    "EX_TREND_01": (
        "For Amex, the repeated negative pattern suggests access and capacity is a "
        "persistent experience issue rather than an isolated monthly spike."
    ),
    "EX_TREND_02": (
        "For Amex, the shift from an almost even June mix to a strongly negative "
        "August mix is substantial, although the observed data does not establish "
        "why it changed."
    ),
    "EX_TREND_03": (
        "For Amex, food and beverage remains a recurring positive element; the "
        "low-volume August reversal is not enough to establish a sustained change."
    ),
}
# Streamlit navigation can discard entrypoint markup, so apply the page bundle here.
apply_base_styles()


def _load_and_validate() -> tuple[pd.DataFrame, ...]:
    brands = load_presentation_dataset("EXECUTIVE_BRAND_COMMENTS")
    themes = load_presentation_dataset("EXECUTIVE_THEME_BRANDS")
    monthly = load_presentation_dataset("EXECUTIVE_THEME_MONTHLY")
    qa = load_presentation_dataset("EXECUTIVE_PRESENTATION_QA")
    insights = load_presentation_dataset("EXECUTIVE_INSIGHTS")
    insight_qa = load_presentation_dataset("EXECUTIVE_INSIGHT_QA")
    brand_evidence = load_csv(BRAND_EVIDENCE_FILE)

    count_columns = [
        "unique_comments",
        "positive_comments",
        "negative_comments",
        "mixed_neutral_comments",
    ]
    require_columns(
        brands,
        [
            "brand",
            "brand_display",
            *count_columns,
            "main_positive_theme",
            "main_positive_aspect",
            "main_pressure_theme",
            "main_pressure_aspect",
        ],
        "EXECUTIVE_BRAND_COMMENTS",
    )
    require_columns(
        themes,
        [
            "brand",
            "executive_theme",
            *count_columns,
            "primary_insight",
            "supported_aspect_count",
        ],
        "EXECUTIVE_THEME_BRANDS",
    )
    require_columns(
        monthly,
        [
            "brand",
            "executive_theme",
            "month",
            *count_columns,
            "theme_comment_balance",
            "monthly_sample_band",
        ],
        "EXECUTIVE_THEME_MONTHLY",
    )
    require_unique(brands, ["brand"], "EXECUTIVE_BRAND_COMMENTS")
    require_unique(themes, ["brand", "executive_theme"], "EXECUTIVE_THEME_BRANDS")
    require_unique(
        monthly,
        ["brand", "executive_theme", "month"],
        "EXECUTIVE_THEME_MONTHLY",
    )
    require_columns(
        brand_evidence,
        [
            "comment_unit_id",
            "brand",
            "executive_theme",
            "detailed_aspect",
            "sentiment_group",
            "post_url",
        ],
        "VOC_PUBLIC_EVIDENCE",
    )
    expected_theme_keys = {
        (brand, theme) for brand in HEADLINE_ISSUERS for theme in THEMES
    }
    actual_theme_keys = set(zip(themes["brand"], themes["executive_theme"]))
    if actual_theme_keys != expected_theme_keys:
        raise DataContractError("Executive theme table does not contain the complete 5 × 4 matrix.")
    if not qa["status"].eq("PASS").all():
        failed = qa.loc[qa["status"].ne("PASS"), "check"].astype(str).tolist()
        raise DataContractError(f"Presentation QA failed: {', '.join(failed)}")
    validate_insights(insights, insight_qa)
    _validate_brand_card_evidence(brands, insights, insight_qa, brand_evidence)
    return brands, themes, monthly, qa, insights, insight_qa


def _insights_with_clear_scope(insights: pd.DataFrame) -> pd.DataFrame:
    """Apply Executive Overview display copy without changing the frozen insight mart."""
    display_insights = insights.copy()
    for insight_id, implication in DISPLAY_IMPLICATION_OVERRIDES.items():
        mask = display_insights["insight_id"].eq(insight_id)
        display_insights.loc[mask, "implication_text"] = implication
    return display_insights


def _safe_text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def _aspect_label(value: object) -> str:
    code = _safe_text(value)
    return ASPECT_LABELS.get(code, code.replace("_", " ").title()) if code else ""


def _validate_brand_card_evidence(
    brands: pd.DataFrame,
    insights: pd.DataFrame,
    insight_qa: pd.DataFrame,
    evidence: pd.DataFrame,
) -> None:
    """Validate each unified brand card against frozen metrics and public evidence."""
    qa_columns = [
        "positive_evidence_comment_id",
        "positive_evidence_url",
        "main_friction",
        "negative_evidence_comment_id",
        "negative_evidence_url",
        "total_comments",
        "positive_comments",
        "negative_comments",
        "mixed_neutral_comments",
        "sentiment_identity_check",
        "source_link_check",
    ]
    require_columns(insight_qa, qa_columns, "EXECUTIVE_INSIGHT_QA")
    brand_insights = insights.loc[insights["section"].eq("Brand-level signals")]
    brand_qa = insight_qa.loc[insight_qa["section"].eq("Brand-level signals")]
    expected = set(HEADLINE_ISSUERS)
    if (
        set(brand_insights["primary_brand"]) != expected
        or set(brand_qa["brand"]) != expected
    ):
        raise DataContractError(
            "Unified brand cards must cover the four headline brands exactly"
        )

    for brand in HEADLINE_ISSUERS:
        summary = brands.loc[brands["brand"].eq(brand)].iloc[0]
        insight_row = brand_insights.loc[
            brand_insights["primary_brand"].eq(brand)
        ].iloc[0]
        qa_row = brand_qa.loc[brand_qa["brand"].eq(brand)].iloc[0]
        if (
            str(qa_row["positive_signal"]) != str(insight_row["evidence_text"])
            or str(qa_row["main_friction"]) != str(insight_row["pressure_text"])
        ):
            raise DataContractError(
                f"Unified {brand} narrative does not match its QA record"
            )
        counts = {
            "total_comments": int(summary["unique_comments"]),
            "positive_comments": int(summary["positive_comments"]),
            "negative_comments": int(summary["negative_comments"]),
            "mixed_neutral_comments": int(summary["mixed_neutral_comments"]),
        }
        if any(int(qa_row[column]) != value for column, value in counts.items()):
            raise DataContractError(
                f"Unified {brand} card counts do not match the frozen summary"
            )
        sentiment_total = (
            counts["positive_comments"]
            + counts["negative_comments"]
            + counts["mixed_neutral_comments"]
        )
        if sentiment_total != counts["total_comments"]:
            raise DataContractError(
                f"Unified {brand} card sentiment counts do not reconcile"
            )
        if (
            str(qa_row["sentiment_identity_check"]) != "PASS"
            or str(qa_row["source_link_check"]) != "PASS"
        ):
            raise DataContractError(f"Unified {brand} card QA is not PASS")

        positive_rows = evidence.loc[
            evidence["comment_unit_id"].eq(str(qa_row["positive_evidence_comment_id"]))
            & evidence["brand"].eq(brand)
            & evidence["sentiment_group"].eq("POSITIVE")
            & evidence["post_url"].eq(str(qa_row["positive_evidence_url"]))
        ]
        positive_aspect = _aspect_label(summary["main_positive_aspect"])
        if positive_aspect:
            positive_rows = positive_rows.loc[
                positive_rows["detailed_aspect"].eq(positive_aspect)
            ]
        else:
            positive_rows = positive_rows.loc[
                positive_rows["executive_theme"].eq("General Lounge Experience")
            ]
        if len(positive_rows) != 1:
            raise DataContractError(
                f"Unified {brand} positive source does not match its signal"
            )

        negative_id = _safe_text(qa_row["negative_evidence_comment_id"])
        negative_url = _safe_text(qa_row["negative_evidence_url"])
        pressure_aspect = _aspect_label(summary["main_pressure_aspect"])
        if negative_id:
            negative_rows = evidence.loc[
                evidence["comment_unit_id"].eq(negative_id)
                & evidence["brand"].eq(brand)
                & evidence["sentiment_group"].eq("NEGATIVE")
                & evidence["post_url"].eq(negative_url)
                & evidence["detailed_aspect"].eq(pressure_aspect)
            ]
            if len(negative_rows) != 1:
                raise DataContractError(
                    f"Unified {brand} negative source does not match its friction"
                )
        elif pressure_aspect or negative_url:
            raise DataContractError(f"Unified {brand} negative source is incomplete")

        for url_column in ("positive_evidence_url", "negative_evidence_url"):
            url = _safe_text(qa_row[url_column])
            if url and not url.startswith("https://www.reddit.com/"):
                raise DataContractError(
                    f"Unified {brand} card contains a non-Reddit source link"
                )


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


def _sentiment_counts(row: pd.Series) -> str:
    return (
        f"{int(row['positive_comments'])} positive · "
        f"{int(row['negative_comments'])} negative · "
        f"{int(row['mixed_neutral_comments'])} mixed/neutral"
    )


def _source_link(url: object, sentiment: str) -> str:
    href = _safe_text(url)
    if not href:
        return ""
    return (
        f'<a class="exec-brand-source" href="{escape(href)}" target="_blank" '
        f'rel="noopener noreferrer">See representative {escape(sentiment)} '
        'comment&nbsp;<span aria-hidden="true">↗</span></a>'
    )


def _render_brand_cards(
    brands: pd.DataFrame,
    insights: pd.DataFrame,
    insight_qa: pd.DataFrame,
) -> None:
    cards = []
    brand_insights = insights.loc[
        insights["section"].eq("Brand-level signals")
    ].set_index("primary_brand")
    brand_qa = insight_qa.loc[
        insight_qa["section"].eq("Brand-level signals")
    ].set_index("brand")
    for brand in HEADLINE_ISSUERS:
        row = brands.loc[brands["brand"].eq(brand)].iloc[0]
        insight = brand_insights.loc[brand]
        qa_row = brand_qa.loc[brand]
        color = ENTITY_COLORS.get(brand, "#3468d4")
        cards.append(
            compact_html(
                f"""
                <article class="exec-brand-card unified" style="--brand-color:{color}">
                    <div class="exec-brand-mark">{brand_logo_img(brand)}<span>{escape(str(row['brand_display']))}</span></div>
                    <div class="exec-brand-headline">{escape(str(insight['headline']))}</div>
                    <div class="exec-brand-interpretation">
                        <div class="exec-brand-signal positive">
                            <span>What stands out positively</span>
                            <strong>{escape(str(insight['evidence_text']))}</strong>
                            {_source_link(qa_row['positive_evidence_url'], 'positive')}
                        </div>
                        <div class="exec-brand-signal pressure">
                            <span>Main friction</span>
                            <strong>{escape(str(insight['pressure_text']))}</strong>
                            {_source_link(qa_row['negative_evidence_url'], 'negative')}
                        </div>
                    </div>
                    <div class="exec-brand-evidence">
                        <div class="exec-brand-evidence-label">Feedback summary</div>
                        <div class="exec-brand-volume"><strong>{int(row['unique_comments']):,}</strong><span>qualifying lounge-experience comments</span></div>
                        {_sentiment_bar(row)}
                        <div class="exec-count-line">{escape(_sentiment_counts(row))}</div>
                    </div>
                </article>
                """
            )
        )
    st.markdown(
        f'<div class="exec-brand-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def _render_theme_matrix(themes: pd.DataFrame) -> None:
    header = "".join(
        f'<div class="exec-matrix-brand">{escape(ENTITY_SHORT_NAMES[brand])}</div>'
        for brand in HEADLINE_ISSUERS
    )
    rows = []
    for theme in THEMES:
        cells = []
        for brand in HEADLINE_ISSUERS:
            row = themes.loc[
                themes["brand"].eq(brand) & themes["executive_theme"].eq(theme)
            ].iloc[0]
            cells.append(
                compact_html(
                    f"""
                    <div class="exec-matrix-cell">
                        <div class="exec-matrix-volume"><strong>{int(row['unique_comments'])}</strong> comments</div>
                        {_sentiment_bar(row, compact=True)}
                        <div class="exec-count-line compact">{escape(_sentiment_counts(row))}</div>
                        <p>{escape(str(row['primary_insight']))}</p>
                    </div>
                    """
                )
            )
        rows.append(
            compact_html(
                f"""
                <div class="exec-matrix-row">
                    <div class="exec-matrix-theme">
                        <div class="exec-matrix-theme-heading">{theme_icon_svg(theme, css_class="theme-row-icon")}<strong>{escape(theme)}</strong></div>
                        <span>{escape(THEME_SUBTHEMES[theme])}</span>
                    </div>
                    {''.join(cells)}
                </div>
                """
            )
        )
    st.markdown(
        compact_html(
            f"""
            <div class="exec-matrix">
                <div class="exec-matrix-header"><div>Experience</div>{header}</div>
                {''.join(rows)}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _heat_color(balance: float, band: str) -> str:
    if pd.isna(balance) or band == "EMPTY":
        return "#f1f3f6"
    neutral = (238, 240, 243)
    directional = (22, 132, 97) if balance >= 0 else (201, 71, 79)
    magnitude = min(abs(float(balance)), 1.0)
    color = tuple(
        round(neutral[channel] + (directional[channel] - neutral[channel]) * magnitude)
        for channel in range(3)
    )
    evidence_alpha = {
        "HIGH": 0.70,
        "MEDIUM": 0.58,
        "LOW": 0.32,
        "VERY_LOW": 0.13,
    }.get(band, 0.13)
    return f"rgba({color[0]},{color[1]},{color[2]},{evidence_alpha:.3f})"


def _render_heat_strip(monthly: pd.DataFrame, theme: str, subdued: bool) -> None:
    data = monthly.loc[monthly["executive_theme"].eq(theme)].copy()
    month_header = "".join(
        f"<span>{label}</span>" for label in MONTH_LABELS.values()
    )
    rows = []
    for brand in HEADLINE_ISSUERS:
        brand_rows = data.loc[data["brand"].eq(brand)].set_index("month")
        cells = []
        for month, label in MONTH_LABELS.items():
            row = brand_rows.loc[month]
            n = int(row["unique_comments"])
            band = str(row["monthly_sample_band"])
            balance = float(row["theme_comment_balance"]) if n else float("nan")
            balance_detail = f" · directional balance {balance:+.1%}" if n else ""
            tooltip = (
                f"{ENTITY_SHORT_NAMES[brand]} · {label} 2026 · {theme} · "
                f"{n} unique comments · {int(row['positive_comments'])} positive · "
                f"{int(row['negative_comments'])} negative · "
                f"{int(row['mixed_neutral_comments'])} mixed/neutral{balance_detail}"
            )
            cells.append(
                f'<span class="exec-heat-cell band-{band.lower()}" '
                f'style="background:{_heat_color(balance, band)}" '
                f'title="{escape(tooltip)}">{"—" if n == 0 else n}</span>'
            )
        rows.append(
            f'<div class="exec-heat-row"><strong>{escape(ENTITY_SHORT_NAMES[brand])}</strong>{"".join(cells)}</div>'
        )
    st.markdown(
        compact_html(
            f"""
            <article class="exec-heat-card{' secondary' if subdued else ''}">
                <div class="exec-heat-title"><h3>{escape(theme)}</h3></div>
                <div class="exec-heat-months"><span class="exec-heat-brand-header">Brand</span>{month_header}</div>
                {''.join(rows)}
            </article>
            """
        ),
        unsafe_allow_html=True,
    )


try:
    brand_summary, theme_summary, monthly, qa, insights, insight_qa = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"The Executive Overview cannot load its presentation data. {error}")
    st.stop()

display_insights = _insights_with_clear_scope(insights)

render_page_header(
    "Executive Overview",
    "A simple view of how lounge feedback differs across Amex, Chase, Capital One and Delta in 2026 YTD.",
)
st.markdown(
    '<div class="exec-period-note">Jan–Aug 2026 · Directional Reddit voice of customer</div>',
    unsafe_allow_html=True,
)

render_section_heading(
    "Brand Performance Overview",
    "How the overall lounge experience differs across Amex, Chase, Capital One and Delta.",
)
_render_brand_cards(brand_summary, insights, insight_qa)

render_section_heading(
    "Experience Drivers",
    "The experience themes shaping lounge feedback across the four brands.",
)
st.markdown(
    compact_html(
        """
        <div class="exec-thin-evidence-note">
            <strong>Amex experience drivers</strong>
            <span>The strongest themes shaping Amex lounge feedback.</span>
        </div>
        """
    ),
    unsafe_allow_html=True,
)
render_insights(display_insights, page="Executive Overview", section="Theme insights")
st.markdown(
    compact_html(
        """
        <div class="exec-thin-evidence-note">
            <strong>Cross-brand theme comparison</strong>
            <span>How the same experience themes compare across all four brands.</span>
        </div>
        """
    ),
    unsafe_allow_html=True,
)
_render_theme_matrix(theme_summary)

render_section_heading(
    "Trend & Momentum",
    "Monthly signals and recurring experience patterns across the measured feedback.",
)
st.markdown(
    compact_html(
        """
        <div class="exec-thin-evidence-note">
            <strong>Amex trend signals</strong>
            <span>The most meaningful changes and recurring patterns in Amex feedback.</span>
        </div>
        """
    ),
    unsafe_allow_html=True,
)
render_insights(display_insights, page="Executive Overview", section="Trend insights")
st.markdown(
    compact_html(
        """
        <div class="exec-thin-evidence-note">
            <strong>Monthly comparison across brands</strong>
            <span>How sentiment direction varies by brand, theme and month.</span>
        </div>
        <div class="exec-heat-legend">
            <span><i class="negative"></i> More negative</span>
            <span><i class="neutral"></i> Balanced</span>
            <span><i class="positive"></i> More positive</span>
            <small>Color shows directional balance. Numbers are comments; fainter cells have less evidence. Hover for the full mix.</small>
        </div>
        """
    ),
    unsafe_allow_html=True,
)
_render_heat_strip(monthly, "General Lounge Experience", subdued=False)

for start in range(0, len(OPERATIONAL_THEMES), 2):
    columns = st.columns(2, gap="large")
    for column, theme in zip(
        columns, OPERATIONAL_THEMES[start : start + 2], strict=True
    ):
        with column:
            _render_heat_strip(monthly, theme, subdued=start >= 2)

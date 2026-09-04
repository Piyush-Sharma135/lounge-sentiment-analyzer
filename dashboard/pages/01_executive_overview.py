"""Executive Overview — a concise national lounge-experience summary."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.layout import render_page_header, render_section_heading
from utils.constants import ENTITY_COLORS, ENTITY_SHORT_NAMES, HEADLINE_ISSUERS
from utils.data_loader import load_presentation_dataset
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
# Streamlit navigation can discard entrypoint markup, so apply the page bundle here.
apply_base_styles()


def _load_and_validate() -> tuple[pd.DataFrame, ...]:
    brands = load_presentation_dataset("EXECUTIVE_BRAND_COMMENTS")
    themes = load_presentation_dataset("EXECUTIVE_THEME_BRANDS")
    monthly = load_presentation_dataset("EXECUTIVE_THEME_MONTHLY")
    qa = load_presentation_dataset("EXECUTIVE_PRESENTATION_QA")

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
    expected_theme_keys = {
        (brand, theme) for brand in HEADLINE_ISSUERS for theme in THEMES
    }
    actual_theme_keys = set(zip(themes["brand"], themes["executive_theme"]))
    if actual_theme_keys != expected_theme_keys:
        raise DataContractError("Executive theme table does not contain the complete 5 × 4 matrix.")
    if not qa["status"].eq("PASS").all():
        failed = qa.loc[qa["status"].ne("PASS"), "check"].astype(str).tolist()
        raise DataContractError(f"Presentation QA failed: {', '.join(failed)}")
    return brands, themes, monthly, qa


def _safe_text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def _aspect_label(value: object) -> str:
    code = _safe_text(value)
    return ASPECT_LABELS.get(code, code.replace("_", " ").title()) if code else ""


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


def _brand_signal(theme: object, aspect: object) -> str:
    theme_text = _safe_text(theme)
    aspect_text = _aspect_label(aspect)
    if not aspect_text:
        return theme_text
    return f"{theme_text} — driven by {aspect_text.lower()}"


def _render_brand_cards(brands: pd.DataFrame) -> None:
    cards = []
    for brand in HEADLINE_ISSUERS:
        row = brands.loc[brands["brand"].eq(brand)].iloc[0]
        color = ENTITY_COLORS.get(brand, "#3468d4")
        cards.append(
            compact_html(
                f"""
                <article class="exec-brand-card" style="--brand-color:{color}">
                    <div class="exec-brand-top">
                        <div class="exec-brand-mark">{escape(str(row['brand_display']))}</div>
                    </div>
                    <div class="exec-brand-volume"><strong>{int(row['unique_comments']):,}</strong><span>lounge-experience comments</span></div>
                    {_sentiment_bar(row)}
                    <div class="exec-count-line">{escape(_sentiment_counts(row))}</div>
                    <div class="exec-brand-signals">
                        <div><span>What stands out positively</span><strong>{escape(_brand_signal(row['main_positive_theme'], row['main_positive_aspect']))}</strong></div>
                        <div><span>Main friction</span><strong>{escape(_brand_signal(row['main_pressure_theme'], row['main_pressure_aspect']))}</strong></div>
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
                    <div class="exec-matrix-theme"><strong>{escape(theme)}</strong><span>{escape(THEME_SUBTHEMES[theme])}</span></div>
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
    base = (22, 132, 97) if balance >= 0 else (201, 71, 79)
    evidence_alpha = {
        "HIGH": 0.70,
        "MEDIUM": 0.58,
        "LOW": 0.32,
        "VERY_LOW": 0.13,
    }.get(band, 0.13)
    alpha = evidence_alpha * (0.40 + 0.60 * min(abs(float(balance)), 1.0))
    return f"rgba({base[0]},{base[1]},{base[2]},{alpha:.3f})"


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
            tooltip = (
                f"{ENTITY_SHORT_NAMES[brand]} · {label} 2026 · {theme} · "
                f"{n} unique comments · {int(row['positive_comments'])} positive · "
                f"{int(row['negative_comments'])} negative · "
                f"{int(row['mixed_neutral_comments'])} mixed/neutral"
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
                <div class="exec-heat-months"><span></span>{month_header}</div>
                {''.join(rows)}
            </article>
            """
        ),
        unsafe_allow_html=True,
    )


try:
    brand_summary, theme_summary, monthly, qa = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"The Executive Overview cannot load its presentation data. {error}")
    st.stop()

render_page_header(
    "Executive Overview",
    "A simple view of how lounge feedback differs across Amex, Chase, Capital One and Delta in 2026 YTD.",
)
st.markdown(
    '<div class="exec-period-note">Jan–Aug 2026 · Directional Reddit voice of customer</div>',
    unsafe_allow_html=True,
)

render_section_heading(
    "Brand experience snapshot",
    "Qualifying Reddit comments with sentiment-bearing lounge experience; each comment is counted once per brand.",
)
st.markdown(
    '<p class="exec-secondary-note">Brand counts are not additive because some Reddit comments discuss more than one brand.</p>',
    unsafe_allow_html=True,
)
_render_brand_cards(brand_summary)

render_section_heading(
    "Lounge experience at a glance",
    "Overall perception first, followed by four broad themes shaping that experience.",
)
st.markdown(
    '<p class="exec-secondary-note">Theme counts are also non-additive because one Reddit comment can discuss more than one part of the lounge experience.</p>',
    unsafe_allow_html=True,
)
_render_theme_matrix(theme_summary)

render_section_heading(
    "How feedback has evolved",
    "Monthly feedback direction across the same five lounge-experience themes.",
)
st.markdown(
    compact_html(
        """
        <div class="exec-heat-legend">
            <span><i class="negative"></i> More negative</span>
            <span><i class="neutral"></i> Balanced</span>
            <span><i class="positive"></i> More positive</span>
            <small>Numbers are comments. Fainter cells have less evidence; hover for the full mix.</small>
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

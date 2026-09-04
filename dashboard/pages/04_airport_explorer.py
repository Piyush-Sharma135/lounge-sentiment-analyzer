"""Airport View - executive airport watchlist and same-location comparisons."""

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.layout import render_page_header, render_section_heading
from utils.constants import DATA_DIR, ENTITY_SHORT_NAMES, HEADLINE_ISSUERS
from utils.data_loader import load_csv
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


apply_base_styles()
if AIRPORT_STYLE_FILE.is_file():
    st.html(f"<style>{AIRPORT_STYLE_FILE.read_text(encoding='utf-8')}</style>")


def _load_and_validate() -> tuple[pd.DataFrame, ...]:
    rows = load_csv(ROWS_FILE)
    battlegrounds = load_csv(BATTLEGROUNDS_FILE)
    summary = load_csv(SUMMARY_FILE)
    qa = load_csv(QA_FILE)
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
    return rows, battlegrounds, summary, qa


def _brand_label(value: str) -> str:
    return "All brands" if value == "ALL" else ENTITY_SHORT_NAMES.get(value, value)


def _summary_value(summary: pd.DataFrame, metric: str) -> int:
    matches = summary.loc[summary["metric"].eq(metric), "value"]
    if len(matches) != 1:
        raise DataContractError(f"Airport summary must contain one row for {metric}")
    return int(matches.iloc[0])


def _safe_text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


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
            drivers.append(
                f'<span><b>{escape(str(row["brand_display"]))}:</b> {escape(str(row["driver_label"]))}</span>'
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
            <span>Main supported signal</span><span>Comparison</span>
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
        f"Frozen Overall Experience result: {float(row['frozen_overall_score_100']):+.1f} "
        f"from {int(row['frozen_overall_comments'])} Overall Experience comments."
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
    )
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
        f"Frozen same-airport comparison result: {float(row['comparison_score_100']):+.1f}; "
        f"same-airport difference: {float(row['same_airport_difference_pp']):+.1f} points."
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
        airport_codes = sorted(battlegrounds["airport_code"].unique())
    else:
        airport_codes = sorted(
            battlegrounds.loc[
                battlegrounds["brand"].eq(selected_brand), "airport_code"
            ].unique()
        )
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
        return "mixed"
    direction = str(group.iloc[0]["presentation_direction"])
    return {"POSITIVE": "positive", "NEGATIVE": "negative"}.get(direction, "mixed")


def _map_figure(
    rows: pd.DataFrame, brand: str, competitive_airports: set[str]
) -> go.Figure:
    colors = {"positive": "#168461", "negative": "#c9474f", "mixed": "#8995a7"}
    points: list[dict[str, object]] = []
    for airport, group in rows.groupby("airport_code"):
        group = group.sort_values("brand_order")
        first = group.iloc[0]
        direction = _map_direction(group, brand)
        if brand == "ALL":
            brand_lines = "<br>".join(
                f"{escape(str(row['brand_display']))}: {int(row['unique_comments'])} comments"
                for _, row in group.iterrows()
            )
            comparison = "Yes" if airport in competitive_airports else "No"
            detail_lines = f"{brand_lines}<br>Brand comparison available: {comparison}"
            marker_comments = int(first["airport_unique_comments"])
        else:
            brand_lines = "<br>".join(
                f"{escape(str(row['brand_display']))}: {int(row['unique_comments'])} comments / "
                f"{int(row['positive_comments'])} positive / {int(row['negative_comments'])} negative / "
                f"{int(row['mixed_neutral_comments'])} mixed/neutral"
                for _, row in group.iterrows()
            )
            detail_lines = brand_lines
            marker_comments = int(first["unique_comments"])
        driver_rows = group.loc[group["driver_label"].notna()].copy()
        driver_line = ""
        if not driver_rows.empty:
            driver_rows["magnitude"] = pd.to_numeric(
                driver_rows["driver_score_100"], errors="coerce"
            ).abs()
            driver = driver_rows.sort_values("magnitude", ascending=False).iloc[0]
            driver_line = f"<br>Main supported signal: {escape(_driver_context(driver))}"
        points.append(
            {
                "airport_code": airport,
                "latitude": float(first["latitude"]),
                "longitude": float(first["longitude"]),
                "direction": direction,
                "color": colors[direction],
                "size": 11 + min(float(np.sqrt(marker_comments)) * 1.7, 13),
                "hover": (
                    f"<b>{escape(str(airport))} - {escape(str(first['airport_name']))}</b><br>"
                    f"{detail_lines}{driver_line if brand != 'ALL' else ''}"
                ),
            }
        )
    points_frame = pd.DataFrame(points)
    figure = go.Figure()
    for direction in ("negative", "mixed", "positive"):
        subset = points_frame.loc[points_frame["direction"].eq(direction)]
        if subset.empty:
            continue
        figure.add_trace(
            go.Scattergeo(
                lon=subset["longitude"],
                lat=subset["latitude"],
                text=subset["airport_code"],
                hovertext=subset["hover"],
                hovertemplate="%{hovertext}<extra></extra>",
                mode="markers+text",
                textposition="top center",
                textfont={"size": 10, "color": "#46546b"},
                marker={
                    "size": subset["size"],
                    "color": subset["color"],
                    "line": {"color": "#ffffff", "width": 1.5},
                    "opacity": 0.86,
                },
                name=direction.title(),
            )
        )
    figure.update_geos(
        scope="usa",
        projection_type="albers usa",
        showland=True,
        landcolor="#eef2f7",
        showlakes=True,
        lakecolor="#ffffff",
        subunitcolor="#d4dce8",
        countrycolor="#c4cedc",
        bgcolor="rgba(0,0,0,0)",
    )
    figure.update_layout(
        height=430,
        margin={"l": 0, "r": 0, "t": 6, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font={"family": "Inter, Segoe UI, sans-serif", "color": "#26334b"},
    )
    return figure


try:
    airport_rows, battleground_rows, airport_summary, airport_qa = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"Airport View cannot load its presentation data. {error}")
    st.stop()

render_page_header(
    "Airport View",
    "See where lounge feedback stands out across US airports and where brands can be compared at the same location.",
)

render_section_heading(
    "Airport experience snapshot",
    "A concise view of sufficiently supported location-level lounge feedback.",
)
snapshot_column, filter_column = st.columns([3.3, 1], gap="large", vertical_alignment="bottom")
with filter_column:
    selected_brand = st.selectbox(
        "Brand",
        BRAND_OPTIONS,
        index=0,
        format_func=_brand_label,
        key="airport_view_brand",
    )
with snapshot_column:
    _snapshot(airport_rows, battleground_rows, selected_brand)

st.markdown(
    compact_html(
        """
        <div class="airport-exec-scope-note">
            <strong>Only airports meeting the frozen evidence threshold are included.</strong>
            Missing airports indicate insufficient evidence, not neutral performance, no lounge, or no Reddit discussion.
        </div>
        """
    ),
    unsafe_allow_html=True,
)

render_section_heading(
    "All supported airports",
    "Complete coverage of every airport meeting the frozen location-specific evidence threshold.",
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
    "Airports standing out positively",
    "Locations where sufficiently supported lounge feedback is especially positive.",
)
positive_count = _render_watchlist(airport_rows, selected_brand, "POSITIVE")

render_section_heading(
    "Where brands can be compared directly",
    "Airports with enough same-location evidence to support a brand comparison.",
)
battleground_count = _render_battlegrounds(battleground_rows, selected_brand)

render_section_heading(
    "View on map",
    "Geographic context for airports with sufficient evidence.",
)
map_rows = _filter_rows(airport_rows, selected_brand)
map_competitive_airports = set(battleground_rows["airport_code"].astype(str))
if selected_brand == "ALL":
    map_legend = '<span><i class="mixed"></i> Supported airport</span>'
else:
    map_legend = '<span><i class="negative"></i> Negative leaning</span><span><i class="mixed"></i> Mixed/balanced</span><span><i class="positive"></i> Positive leaning</span>'
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
st.caption(
    "One marker is shown per supported airport. All-brands markers are neutral because no combined cross-brand airport score is manufactured. With a specific brand selected, color reflects that brand's comment composition. Marker size reflects unique qualifying comments."
)

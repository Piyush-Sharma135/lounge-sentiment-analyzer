"""FAQ / Methodology — trust, transparency, and documentation layer."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from components.layout import render_page_header, render_section_heading
from components.methodology import (
    compact_validation_table,
    render_definition_pair,
    render_example_card,
    render_faq_cards,
    render_funnel,
    render_glossary,
    render_info_cards,
    render_jump_links,
    render_metric_cards,
    render_theme_cards,
)
from utils.constants import DATA_DIR
from utils.data_loader import load_canonical_dataset, load_csv, load_home_frozen_summaries
from utils.html import compact_html
from utils.validation import DataContractError, require_columns, require_unique


STYLE_FILE = Path(__file__).resolve().parents[1] / "assets" / "styles" / "methodology.css"
FAQ_METHODOLOGY_STATUS = "FAQ_METHODOLOGY_FINAL_FROZEN"

VALIDATION_SUMMARY_FILE = DATA_DIR / "58_validation_summary.csv"
EXECUTIVE_RECONCILIATION_FILE = DATA_DIR / "56_executive_population_reconciliation.csv"
EXECUTIVE_BRAND_FILE = DATA_DIR / "56_executive_brand_comment_summary.csv"
EXECUTIVE_THEME_FILE = DATA_DIR / "56_executive_theme_brand_summary.csv"
EXECUTIVE_MONTHLY_FILE = DATA_DIR / "56_executive_theme_monthly.csv"
AIRPORT_SUMMARY_FILE = DATA_DIR / "57_airport_view_summary.csv"
VOC_EXAMPLES_FILE = DATA_DIR / "58_voc_display_public.csv"

FUNNEL_KEYS = (
    ("exploded_comments", "Exploded Reddit comment units"),
    ("experience_bearing", "Experience-bearing after Stage 1"),
    ("analysis_window", "2026 YTD production scope"),
    ("usable_comments", "Stage 2A-1 usable"),
    ("known_comments", "Known-attribution Stage 2B population"),
    ("extracted_observations", "Stage 2B extracted observations"),
    ("clean_observations", "Final clean observations"),
)

THEMES = (
    ("General Lounge Experience", "Overall impression of the lounge experience"),
    ("Access & Capacity", "Crowding · Wait time & queues · Seating · Access · Reservations"),
    ("Food & Beverage", "Food quality · Food availability · Beverage & bar"),
    ("Service & Upkeep", "Staff & service · Cleanliness"),
    (
        "Space, Amenities & Convenience",
        "Ambience · Amenities · Wi-Fi/workspace · Family/children · Location · Hours · Value",
    ),
)


def _metric(frame: pd.DataFrame, name: str, dataset: str) -> int:
    require_columns(frame, ["metric", "value"], dataset)
    rows = frame.loc[frame["metric"].astype(str).eq(name), "value"]
    if len(rows) != 1:
        raise DataContractError(f"{dataset} must contain one row for {name!r}")
    value = pd.to_numeric(rows.iloc[0], errors="coerce")
    if pd.isna(value):
        raise DataContractError(f"{dataset} has a non-numeric value for {name!r}")
    return int(value)


def _section(anchor: str, title: str, description: str = "") -> None:
    paragraph = f"<p>{escape(description)}</p>" if description else ""
    st.markdown(
        compact_html(
            f"""
            <div id="{escape(anchor)}" class="section-heading method-section-heading">
                <div><h2>{escape(title)}</h2>{paragraph}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _load_and_validate() -> dict[str, object]:
    funnel = load_canonical_dataset("FAQ_FUNNEL")
    aspects = load_canonical_dataset("FAQ_ASPECT_GLOSSARY")
    sources = load_canonical_dataset("FAQ_SOURCES")
    limitations = load_canonical_dataset("FAQ_LIMITATIONS")
    examples = load_canonical_dataset("FAQ_EXAMPLES")
    score_glossary = load_canonical_dataset("FAQ_SCORE_GLOSSARY")
    frozen = load_home_frozen_summaries()
    validation = load_csv(VALIDATION_SUMMARY_FILE)
    reconciliation = load_csv(EXECUTIVE_RECONCILIATION_FILE)
    brand_summary = load_csv(EXECUTIVE_BRAND_FILE)
    theme_summary = load_csv(EXECUTIVE_THEME_FILE)
    monthly = load_csv(EXECUTIVE_MONTHLY_FILE)
    airport = load_csv(AIRPORT_SUMMARY_FILE)
    voc_examples = load_csv(VOC_EXAMPLES_FILE)

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
    expected_counts = {
        "exploded_comments": 61413,
        "experience_bearing": 17742,
        "analysis_window": 5850,
        "usable_comments": 3696,
        "known_comments": 2215,
        "extracted_observations": 6003,
        "clean_observations": 5997,
    }
    if counts != expected_counts:
        raise DataContractError(f"Frozen FAQ funnel changed: {counts}")

    population = frozen["production_population"]
    stage2a_summary = frozen["stage2a1"]
    stage2b_population = frozen["stage2b_population"]
    freeze_summary = frozen["stage2b_freeze"]
    cross_checks = (
        (counts["experience_bearing"], _metric(population, "historical_stage1_experience_candidates", "PRODUCTION_POPULATION")),
        (counts["analysis_window"], _metric(population, "ytd_candidate_rows", "PRODUCTION_POPULATION")),
        (counts["usable_comments"], _metric(stage2a_summary, "usable_rows", "STAGE2A1_SUMMARY")),
        (counts["known_comments"], _metric(stage2b_population, "stage2B_api_candidate_comments", "STAGE2B_POPULATION")),
        (counts["extracted_observations"], _metric(freeze_summary, "production_observations", "STAGE2B_FREEZE")),
        (counts["clean_observations"], _metric(freeze_summary, "final_clean_observations", "STAGE2B_FREEZE")),
    )
    if any(left != right for left, right in cross_checks):
        raise DataContractError("FAQ funnel conflicts with frozen production summaries")

    require_columns(
        validation,
        ["validation_stage", "benchmark_type", "metric_name", "metric_value"],
        "VALIDATION_SUMMARY",
    )

    def validation_metrics(stage: str) -> dict[str, float]:
        rows = validation.loc[
            validation["validation_stage"].eq(stage)
            & validation["benchmark_type"].eq("overall")
        ]
        return {
            str(row.metric_name): float(row.metric_value)
            for row in rows.itertuples(index=False)
        }

    stage1_metrics = validation_metrics("EXPERIENCE_BEARING")
    expected_stage1 = {"Accuracy": 0.925, "Precision": 0.880, "Recall": 0.917, "F1": 0.898}
    if any(round(stage1_metrics[key], 3) != value for key, value in expected_stage1.items()):
        raise DataContractError(f"Stage 1 validation metrics changed: {stage1_metrics}")

    stage2a_metrics = validation_metrics("DETAILED_USABILITY")
    expected_stage2a = {"Accuracy": 0.904, "Precision": 0.935, "Recall": 0.935, "F1": 0.935}
    if any(round(stage2a_metrics[key], 3) != value for key, value in expected_stage2a.items()):
        raise DataContractError(f"Usability validation metrics changed: {stage2a_metrics}")

    entity_rows = validation.loc[
        validation["validation_stage"].eq("ENTITY_ASSIGNMENT")
    ]
    entity_qa = entity_rows.pivot(
        index="benchmark_type", columns="metric_name", values="metric_value"
    ).reset_index().rename(
        columns={
            "benchmark_type": "metric",
            "Precision": "precision",
            "Recall": "recall",
            "F1": "f1",
        }
    )
    entity_order = {"issuer": 0, "network": 1, "issuer_network_pair": 2}
    entity_qa = entity_qa.assign(
        _order=entity_qa["metric"].map(entity_order)
    ).sort_values("_order").drop(columns="_order").reset_index(drop=True)
    require_columns(entity_qa, ["metric", "precision", "recall", "f1"], "ENTITY_QA")
    require_columns(reconciliation, ["metric", "value", "definition"], "EXECUTIVE_RECONCILIATION")
    require_unique(reconciliation, ["metric"], "EXECUTIVE_RECONCILIATION")
    require_columns(brand_summary, ["brand_display", "unique_comments"], "EXECUTIVE_BRAND_SUMMARY")
    require_columns(theme_summary, ["executive_theme"], "EXECUTIVE_THEME_SUMMARY")
    require_columns(monthly, ["monthly_sample_band"], "EXECUTIVE_MONTHLY")
    require_columns(airport, ["metric", "value"], "AIRPORT_SUMMARY")
    require_columns(sources, ["subreddit", "comments"], "FAQ_SOURCES")
    require_columns(examples, ["comment_unit_id", "post_title", "comment_text", "post_url", "aspect", "sentiment", "evidence"], "FAQ_EXAMPLES")
    require_columns(score_glossary, ["metric", "definition", "scale_or_use"], "FAQ_SCORE_GLOSSARY")

    recon_values = reconciliation.set_index("metric")["value"].astype(int).to_dict()
    required_recon = {
        "stage2b_total_comments": 2215,
        "headline_issuer_attributed_comments": 1566,
        "four_brand_sentiment_union": 988,
        "multi_brand_comments": 192,
        "issuer_unknown_comments": 857,
        "unknown_issuer_known_network_comments": 570,
        "issuer_other_comments": 115,
        "only_nonheadline_comments": 649,
        "no_sentiment_excluded_comments": 15,
        "outside_executive_union": 1227,
        "outside_non_primary_cohort": 682,
        "outside_primary_without_headline_issuer": 510,
        "outside_primary_without_qualifying_observation": 20,
        "outside_primary_only_no_sentiment": 15,
    }
    if any(recon_values.get(key) != value for key, value in required_recon.items()):
        raise DataContractError("Executive population reconciliation no longer matches the freeze QA")

    expected_brands = {"Amex": 508, "Chase": 328, "Capital One": 214, "Delta": 159}
    actual_brands = brand_summary.set_index("brand_display")["unique_comments"].astype(int).to_dict()
    if actual_brands != expected_brands:
        raise DataContractError(f"Frozen brand comment counts changed: {actual_brands}")
    if set(theme_summary["executive_theme"].astype(str)) != {title for title, _ in THEMES}:
        raise DataContractError("FAQ theme mapping conflicts with the frozen Executive Overview")
    if set(monthly["monthly_sample_band"].dropna().astype(str)) - {"HIGH", "MEDIUM", "LOW", "VERY_LOW", "EMPTY"}:
        raise DataContractError("Unexpected monthly sample band in frozen Executive Overview data")
    if _metric(airport, "absolute_eligible_airports", "AIRPORT_SUMMARY") != 16:
        raise DataContractError("Supported-airport count changed")
    if _metric(airport, "competitive_airports", "AIRPORT_SUMMARY") != 5:
        raise DataContractError("Competitive-airport count changed")
    if _metric(freeze_summary, "material_evidence_failures", "STAGE2B_FREEZE") != 6:
        raise DataContractError("Material evidence-failure count changed")

    return {
        "counts": counts,
        "aspects": aspects,
        "sources": sources,
        "limitations": limitations,
        "examples": examples,
        "score_glossary": score_glossary,
        "stage1_metrics": stage1_metrics,
        "stage2a_metrics": stage2a_metrics,
        "entity_qa": entity_qa,
        "reconciliation": reconciliation,
        "brand_counts": expected_brands,
        "voc_examples": voc_examples,
    }


if STYLE_FILE.is_file():
    st.html(f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>")

try:
    data = _load_and_validate()
except (FileNotFoundError, KeyError, ValueError, DataContractError) as error:
    st.error(f"FAQ / Methodology cannot load its frozen documentation sources safely. {error}")
    st.stop()

counts = data["counts"]
aspects = data["aspects"]
sources = data["sources"]
examples = data["examples"]
stage1_metrics = data["stage1_metrics"]
stage2a_metrics = data["stage2a_metrics"]
entity_qa = data["entity_qa"]
reconciliation = data["reconciliation"]
brand_counts = data["brand_counts"]
voc_examples = data["voc_examples"]
assert isinstance(counts, dict)
assert isinstance(aspects, pd.DataFrame)
assert isinstance(sources, pd.DataFrame)
assert isinstance(examples, pd.DataFrame)
assert isinstance(stage1_metrics, dict)
assert isinstance(stage2a_metrics, dict)
assert isinstance(entity_qa, pd.DataFrame)
assert isinstance(reconciliation, pd.DataFrame)
assert isinstance(brand_counts, dict)
assert isinstance(voc_examples, pd.DataFrame)

render_page_header(
    "FAQ / Methodology",
    "How the Reddit lounge analysis was built, validated and interpreted.",
    eyebrow="REDDIT LOUNGE INTELLIGENCE",
)
st.markdown(
    '<div class="method-intro-strip">Business-friendly answers appear first. Open the technical details beneath each section for definitions, controls and frozen production references.</div>',
    unsafe_allow_html=True,
)

_section("common-questions", "Common questions")
render_jump_links(
    (
        ("How the analysis was built", "analysis-built"),
        ("What counted as lounge experience", "lounge-experience"),
        ("Attribution", "attribution"),
        ("Themes & sentiment", "themes-sentiment"),
        ("Comment counting", "counting-rules"),
        ("Analytical score & uncertainty", "score-uncertainty"),
        ("Airport methodology", "airport-methodology"),
        ("Monthly analysis", "monthly-analysis"),
        ("Source robustness", "source-robustness"),
        ("Validation", "validation"),
        ("Limitations", "limitations"),
        ("Examples", "real-examples"),
        ("Glossary", "glossary"),
    )
)
render_faq_cards(
    (
        ("What does this dashboard analyze?", "It analyzes how Reddit users describe airport lounge experiences across four headline brands, detailed experience areas and supported airports. Results cover Jan–Aug 2026.", "analysis-built"),
        ("Why use Reddit comments?", "Reddit provides detailed, unsolicited descriptions of real lounge experiences. It is useful directional feedback, but it is not a representative customer survey.", "source-robustness"),
        ("Why don’t brand counts add up?", "A single comment can discuss more than one brand or experience theme. It can therefore appear in multiple views while still being counted only once within each displayed brand or theme.", "counting-rules"),
        ("What is a comment versus an observation?", "A comment is one Reddit response. An observation is one supported brand or lounge × experience area × sentiment proposition extracted from that response.", "counting-rules"),
        ("How are brands and airports assigned?", "Direct evidence in the comment is preferred. Titles can clarify a unique reference under constrained rules, while uncertain attribution remains UNKNOWN.", "attribution"),
        ("What does positive, negative or mixed mean?", "Each supported experience proposition receives a frozen sentiment label. Executive views combine mixed and neutral outcomes, while comments without directional sentiment are excluded from distributions.", "themes-sentiment"),
        ("Why are some airports missing?", "Airport View shows only locations meeting the frozen evidence rules. A missing airport means insufficient supported evidence—not neutral performance or the absence of a lounge.", "airport-methodology"),
        ("Is this representative of all lounge customers?", "No. Reddit users and communities are self-selected, and discussion volume varies substantially. The dashboard should be read as directional customer feedback within the measured population.", "limitations"),
    )
)

_section("analysis-built", "How the analysis was built", "The final frozen analysis funnel, expressed in business language.")
render_funnel(counts)
with st.expander("Technical pipeline detail", expanded=False):
    st.markdown(
        """
- **61,413** exploded comment units entered Stage 1.
- **17,742** were classified as `DIRECT_EXPERIENCE`, `SECOND_HAND_EXPERIENCE` or `GENERAL_EXPERIENCE_OPINION`.
- **5,850** fell between January 1 and August 31, 2026 using the parent post date.
- **3,696** passed Stage 2A-1 usability review.
- **2,215** had at least one known attributed brand or lounge for Stage 2B extraction.
- **6,003** brand/lounge × detailed aspect × sentiment observations were extracted.
- **6** material evidence failures were removed, leaving **5,997** clean observations.
"""
    )

_section("lounge-experience", "What counted as lounge experience?")
render_info_cards(
    (
        ("Included", "Personal lounge experiences, reported experiences from another traveler, and general opinions grounded in lounge experience."),
        ("Not automatically included", "Access-policy or card-only discussion, questions without experience evidence, news, generic lounge discussion, and irrelevant content."),
    )
)
st.markdown('<div class="method-callout">Keyword presence alone did not make a comment experience-bearing. The comment needed to communicate a defensible experience proposition.</div>', unsafe_allow_html=True)
with st.expander("Technical classification detail", expanded=False):
    st.markdown(
        "Stage 1 asks whether a comment contains lounge-experience feedback. The three included production classes are "
        "`DIRECT_EXPERIENCE`, `SECOND_HAND_EXPERIENCE`, and `GENERAL_EXPERIENCE_OPINION`. "
        "Other classes remain documented in the frozen relevance taxonomy but do not automatically enter detailed experience analysis."
    )

_section("comment-title-context", "What information from a Reddit thread was used?")
render_info_cards(
    (
        ("Primary evidence", "Individual Reddit comment text was the main analytical unit."),
        ("Supporting context", "Thread titles were used only when one clear target could safely resolve phrases such as ‘there’, ‘that lounge’ or ‘this place’."),
        ("Not a separate experience unit", "Original post bodies were not systematically converted into independent experience observations."),
        ("Conservative scope", "A lounge-bearing title alone did not create an observation when the comment lacked an experience proposition or a defensible referential link."),
    )
)
st.markdown('<div class="method-callout warm">This is a documented scope limitation; missing context was not silently inferred.</div>', unsafe_allow_html=True)
with st.expander("How comment and title context were used", expanded=False):
    title_example = examples.loc[examples["comment_unit_id"].eq("comment_0000527")].iloc[0]
    st.markdown(
        f"**Comment-explicit context:** A comment that names the brand or lounge needs no title inheritance.\n\n"
        f"**Constrained title resolution:** In the frozen example titled *{title_example['post_title']}*, the comment explicitly says "
        f"‘{title_example['evidence']}’ The brand comes from the comment; the IAD airport context is resolved from the single clear Dulles target in the title.\n\n"
        "**No proposition:** A relevant title by itself is insufficient. The comment still has to express an experience or link clearly back to the title’s single target."
    )

_section("stage2a", "Why did some experience-related comments still get excluded?")
render_definition_pair(
    "Is this about lounge experience?",
    "The first classification identifies comments that communicate direct, second-hand or broader experience-based feedback.",
    "Is it specific enough for detailed analysis?",
    "The next quality check asks whether the experience supports reliable attribution, experience-area extraction and sentiment extraction.",
)
st.markdown('<div class="method-callout">A comment could be broadly experience-related yet still be too vague for detailed analysis. This explains the reduction from 5,850 to 3,696 comments.</div>', unsafe_allow_html=True)

_section("attribution", "How were brands, lounges and airports attributed?")
render_info_cards(
    (
        ("Direct evidence first", "Explicit brand, lounge and airport evidence in the comment is preferred."),
        ("Titles under constraints", "Title resolution is allowed only when a reference has one clear target."),
        ("Airports use a stricter bar", "Airport context remains missing unless the location can be defended precisely."),
        ("UNKNOWN over false certainty", "Unresolved attribution is retained as UNKNOWN rather than assigned to the wrong place or brand."),
    )
)
st.markdown('<div class="method-callout warm"><strong>Priority Pass nuance:</strong> Priority Pass identifies an access program, not automatically a physical lounge network. Access-program and physical-lounge identity remain separate.</div>', unsafe_allow_html=True)
with st.expander("What does primary analysis mean? — technical detail", expanded=False):
    st.markdown(
        """
Headline issuer brands are **Amex, Chase, Capital One and Delta**. The underlying extraction also retains supported physical lounge networks and programs, including Centurion, Capital One Lounge, Capital One Landing, Sapphire Lounge, Priority Pass, Plaza Premium, Escape and Delta Sky Club. Networks do not necessarily map one-to-one to an issuer.

Headline analysis uses the approved primary cohort. Title-resolved evidence is retained as a robustness layer. Because the primary cohort is defined at comment level, a primary comment can still contain some title-resolved observations; the primary file should not be interpreted as every row being `COMMENT_EXPLICIT`.
"""
    )

_section("themes-sentiment", "What parts of the lounge experience were analyzed?")
render_theme_cards(THEMES)
st.markdown('<div class="method-callout">The five themes are presentation groups only. The underlying extracted detailed aspect never changes.</div>', unsafe_allow_html=True)
with st.expander("View detailed aspect taxonomy", expanded=False):
    detail = aspects.rename(columns={"aspect": "Detailed aspect", "definition": "Definition"}).copy()
    compact_validation_table(detail)

render_section_heading("How was sentiment classified?")
render_info_cards(
    (
        ("Positive", "The experience proposition communicates a favorable judgment."),
        ("Negative", "The experience proposition communicates an unfavorable judgment."),
        ("Mixed / neutral", "Executive display combines frozen MIXED and NEUTRAL outcomes."),
        ("No sentiment", "NO_SENTIMENT is retained in the underlying data but excluded from sentiment-bearing distributions."),
    )
)
with st.expander("Frozen sentiment labels", expanded=False):
    st.markdown("`POSITIVE` · `NEGATIVE` · `MIXED` · `NEUTRAL` · `NO_SENTIMENT`")

_section("counting-rules", "How is one comment counted when it mentions several things?")
render_definition_pair(
    "One Reddit response",
    "The comment is the primary unit shown in executive counts.",
    "One supported experience proposition",
    "An observation binds a brand or lounge, detailed experience area and sentiment to exact evidence.",
)
st.markdown('<div class="method-callout"><strong>Illustrative example:</strong> “The lounge was crowded, the food was good, but I couldn’t find a seat.” This can produce Crowding → Negative, Food quality → Positive and Seating availability → Negative, but it still counts as one Reddit comment in a comment-level view.</div>', unsafe_allow_html=True)
with st.expander("Exact executive comment-collapse rule", expanded=False):
    st.markdown("Observations are collapsed back to one sentiment outcome per **brand × comment**, **brand × theme × comment**, or **brand × airport × comment** where relevant.")
    st.markdown(
        """
1. Remove `NO_SENTIMENT`.
2. If any `MIXED` exists, classify the comment as Mixed / neutral.
3. Otherwise, if both positive and negative occur, classify it as Mixed / neutral.
4. Otherwise, positive-only becomes Positive.
5. Otherwise, negative-only becomes Negative.
6. Neutral-only becomes Mixed / neutral.

Neutral does not override otherwise consistently positive or negative evidence.
"""
    )

render_section_heading("Why don’t the counts always add up?")
render_info_cards(
    (
        ("Themes can overlap", "One comment can discuss several parts of the lounge experience."),
        ("Brands can overlap", "A comparative comment can legitimately discuss more than one headline brand."),
    )
)
st.markdown('<div class="method-callout warm"><strong>Frozen Amex example:</strong> 859 theme appearances come from 508 unique comments. The union remains 508 because some comments appear in more than one theme.</div>', unsafe_allow_html=True)
with st.expander("Why Executive Overview contains fewer comments than detailed extraction", expanded=False):
    recon = reconciliation.set_index("metric")["value"].astype(int)
    st.markdown(
        f"""
- Detailed-extraction comments: **{recon['stage2b_total_comments']:,}**
- Attributed to at least one headline issuer before later filtering: **{recon['headline_issuer_attributed_comments']:,}**
- Primary sentiment-bearing four-brand union: **{recon['four_brand_sentiment_union']:,}**
- Comments contributing to two or more headline issuers: **{recon['multi_brand_comments']:,}**
- Comments with an UNKNOWN issuer assignment: **{recon['issuer_unknown_comments']:,}**
- UNKNOWN-only issuer with a known lounge/network: **{recon['unknown_issuer_known_network_comments']:,}**
- Includes OTHER issuer: **{recon['issuer_other_comments']:,}**
- Non-headline brands or networks only: **{recon['only_nonheadline_comments']:,}**
- Only `NO_SENTIMENT`: **{recon['no_sentiment_excluded_comments']:,}** distinct comments

The **1,227** comments outside the executive union reconcile as 682 outside the primary cohort, 510 primary comments without a headline issuer, 20 without a qualifying headline observation, and 15 with only `NO_SENTIMENT`.
"""
    )
    render_metric_cards(tuple((f"{value:,}", brand, "Unique qualifying comments") for brand, value in brand_counts.items()))

_section("score-uncertainty", "What is the analytical sentiment score?")
st.markdown('<div class="method-formula">Sentiment Score = (Positive − Negative) ÷ sentiment-bearing observations × 100</div>', unsafe_allow_html=True)
render_info_cards(
    (
        ("−100", "All sentiment-bearing observations are negative."),
        ("0", "Positive and negative direction is balanced."),
        ("+100", "All sentiment-bearing observations are positive."),
        ("What it is not", "It is not NPS, a satisfaction percentage, market share or an estimate for all lounge customers."),
    )
)
st.markdown("The score supports ranking, peer comparison, confidence analysis and internal statistical testing. Executive pages primarily show unique comments and positive, negative and mixed/neutral composition because those are easier to interpret directly.")
with st.expander("Frozen score definitions", expanded=False):
    score_definitions = data["score_glossary"]
    assert isinstance(score_definitions, pd.DataFrame)
    compact_validation_table(
        score_definitions.rename(
            columns={"metric": "Metric", "definition": "Definition", "scale_or_use": "Scale or use"}
        )
    )

render_section_heading("How was uncertainty estimated?")
render_info_cards(
    (
        ("One score per brand × comment", "The headline Overall Experience interval starts from primary explicit evidence and prevents repeated observations from overweighting a comment."),
        ("4,000 resamples", "Comments are sampled with replacement, using the same number of comments in each resample, and the metric is recalculated."),
        ("95% estimate range", "The 2.5th and 97.5th percentiles form the interval. A narrower range generally indicates a more precise estimate."),
        ("Correct interpretation", "The interval describes repeated-sample uncertainty; it is not a 95% probability statement about the true score."),
    )
)
with st.expander("Historical Attribute Experience Index detail", expanded=False):
    st.markdown("The historical Attribute Experience Index used comment-level attribute scores and **2,000** bootstrap resamples. The final executive pages no longer feature that index prominently; it remains documented for analytical continuity.")

_section("competitive-comparisons", "How were brands compared?")
render_definition_pair(
    "Absolute experience",
    "How positive or negative is the selected brand’s feedback on its own?",
    "Relative position",
    "How does that score compare with other sufficiently sampled brands?",
)
st.markdown('<div class="method-formula">Difference vs sampled peers = selected brand score − sampled peer score</div>', unsafe_allow_html=True)
st.markdown("A brand can outperform sampled competitors while its feedback is still negative. It can also have positive feedback while trailing stronger competitors.")
with st.expander("Technical competitive-position labels", expanded=False):
    st.markdown("The frozen layer retains labels such as `TRUE_STRENGTH`, `TRUE_WEAKNESS`, `LESS_BAD_THAN_PEERS`, `GOOD_BUT_BEHIND_PEERS`, `PEER_PARITY` and `MIXED_POSITION`. Executive pages translate these into plain business English.")

_section("airport-methodology", "How does Airport View decide what to show?")
render_metric_cards(
    (
        ("16", "Supported airports", "Meet the frozen absolute-evidence rules"),
        ("5", "Competitive airports", "Have valid same-airport peer evidence"),
        ("Head-to-head", "One-peer comparison", "Used when only one qualifying peer exists"),
        ("Insufficient evidence", "Missing airport", "Never interpreted as neutral performance or no lounge"),
    )
)
st.markdown("Same-airport comparisons are made only where enough location-specific evidence exists. A national peer comparison is never substituted for a same-airport comparison.")
with st.expander("Airport ranking and displayed-composition detail", expanded=False):
    st.markdown("Airport watchlist placement may use the frozen Overall Experience ranking logic. The displayed positive/negative/mixed composition can use the broader eligible all-experience brand-airport population. The ranking denominator and displayed composition may therefore differ; this is intentional.")

_section("monthly-analysis", "How should monthly patterns be interpreted?")
render_info_cards(
    (
        ("Time proxy", "Month is assigned from the parent Reddit post date because individual comment timestamps were unavailable."),
        ("Heat-strip shading", "Presentation shading uses (positive comments − negative comments) ÷ sentiment-bearing comments."),
        ("Evidence weight", "Lower-evidence months are visually muted rather than removed solely because the sample is small."),
        ("Avoid endpoint stories", "Do not infer a trend solely from January and August; review the full pattern and monthly evidence."),
    )
)
with st.expander("Frozen monthly evidence bands", expanded=False):
    st.markdown("The presentation dataset retains `HIGH`, `MEDIUM`, `LOW` and `VERY_LOW` evidence bands, plus `EMPTY` where no eligible monthly result exists. The heat-strip balance is a presentation metric and does not replace the frozen analytical sentiment score.")

_section("source-robustness", "Could subreddit mix affect the results?")
st.markdown('<div class="method-callout warm">Yes. A large share of the measured discussion comes from a small number of brand and access-program communities. Raw Reddit discussion volume is not market share.</div>', unsafe_allow_html=True)
render_info_cards(
    (
        ("Consistent across communities", "Direction and magnitude are similar across source groups with enough evidence."),
        ("Same direction across communities", "The result stays positive or negative, but its size varies."),
        ("Varies across communities", "The conclusion changes depending on which source communities are included."),
        ("Limited community coverage", "There is not enough evidence across several source groups for a reliable robustness assessment."),
    )
)
with st.expander("Source-community coverage", expanded=False):
    ranked = sources.sort_values("comments", ascending=False)[["subreddit", "comments"]].copy()
    ranked["subreddit"] = "r/" + ranked["subreddit"].astype(str)
    ranked["comments"] = pd.to_numeric(ranked["comments"], errors="raise").astype(int)
    ranked.columns = ["Reddit community", "Qualifying comments"]
    compact_validation_table(ranked)
    st.caption("Source groups used for robustness analysis include home-brand, general, and other/non-home communities.")

_section("validation", "How was model quality checked?")
st.markdown("**Experience-bearing classification**")
render_metric_cards(tuple((f"{stage1_metrics[key]:.3f}", key, "200-comment frozen validation set") for key in ("Accuracy", "Precision", "Recall", "F1")))
st.markdown("**Detailed-usability classification**")
render_metric_cards(tuple((f"{stage2a_metrics[key]:.3f}", key, "Final integrated usability benchmark") for key in ("Accuracy", "Precision", "Recall", "F1")))
st.markdown('<div class="method-callout warm"><strong>Important:</strong> Gold labels were assistant-reviewed rather than independently human-annotated. These results support production QA but are not an independent human benchmark.</div>', unsafe_allow_html=True)
with st.expander("Entity-assignment benchmark", expanded=False):
    entity_display = entity_qa.copy()
    entity_display["metric"] = entity_display["metric"].map({"issuer": "Issuer assignment", "network": "Physical lounge network", "issuer_network_pair": "Issuer + network pair"}).fillna(entity_display["metric"])
    for column in ("precision", "recall", "f1"):
        entity_display[column] = entity_display[column].map(lambda value: f"{float(value):.3f}")
    entity_display.columns = ["Assignment", "Precision", "Recall", "F1"]
    compact_validation_table(entity_display)
    st.caption("Final post-audit resolver evaluation; conservative UNKNOWN retention remains part of the design.")

render_section_heading("How was extracted evidence checked?")
render_info_cards(
    (
        ("Exact support", "Each retained proposition preserves the exact supporting text span."),
        ("Valid binding", "Quality checks verify that the evidence supports the assigned brand or lounge."),
        ("Duplicate control", "Repeated brand/lounge × aspect groups were checked before freeze."),
        ("Final removal", "Six material evidence failures were removed: 6,003 extracted observations became 5,997 clean observations."),
    )
)

_section("voc-methodology", "How are Voice of Customer quotes selected?")
render_info_cards(
    (
        ("Deterministic curation", "Quotes are selected from a frozen evidence mart, not randomly generated or chosen at runtime."),
        ("Display quality", "Prominent examples prioritize clear attribution, standalone meaning, evidence quality, executive safety and brand/theme relevance."),
        ("Context, not prevalence", "Quote counts do not indicate how frequently an opinion occurs."),
        ("Measured distribution", "The sentiment population shown above the quotes provides the prevalence within the selected Reddit comment population."),
    )
)

_section("limitations", "What are the main limitations?")
limitations_list = (
    "Reddit users are not representative of all lounge customers.",
    "Source communities are concentrated.",
    "Brand and community discussion volume is unequal.",
    "Discussion volume is not market share.",
    "No demographic or customer-value weighting is applied.",
    "The analysis is observational and does not establish causality.",
    "Individual comment timestamps were unavailable; parent post date is used.",
    "Original post bodies were not systematically analyzed as standalone experience observations.",
    "UNKNOWN attribution is intentionally retained where certainty is insufficient.",
    "Airport and physical-lounge-network coverage is uneven.",
    "Some monthly theme cells are sparse.",
    "Community composition can affect observed sentiment.",
    "Validation gold was assistant-reviewed rather than independently human-labeled.",
)
render_info_cards(tuple((f"{index:02d}", text) for index, text in enumerate(limitations_list, start=1)))
with st.expander("Canonical limitation notes", expanded=False):
    canonical_limitations = data["limitations"]
    assert isinstance(canonical_limitations, pd.DataFrame)
    compact_validation_table(canonical_limitations.rename(columns={"topic": "Topic", "limitation": "Documented limitation"}))

_section("real-examples", "Examples of how the methodology works", "Frozen Reddit examples make the attribution and counting rules auditable.")


def _faq_example(comment_id: str) -> pd.DataFrame:
    rows = examples.loc[examples["comment_unit_id"].eq(comment_id)].copy()
    if rows.empty:
        raise DataContractError(f"Required FAQ example is missing: {comment_id}")
    return rows


example_specs = (
    ("Comment-explicit attribution", "The comment names enough context", "comment_0000413", "Capital One is supported directly by the comment; no title inheritance is required."),
    ("Constrained title context", "The title supplies one clear airport", "comment_0000527", "Chase is explicit in the comment, while Dulles/IAD is resolved from the uniquely targeted title."),
    ("UNKNOWN retained", "Access program does not force an issuer", "comment_0000547", "Priority Pass is supported, but the issuer remains UNKNOWN because an access program does not uniquely identify one issuer."),
    ("Mixed and multi-observation evidence", "One comment can express several judgments", "comment_0002181", "The same Amex/Centurion comment supports negative food, positive beverage and mixed value judgments."),
)
for label, title, comment_id, explanation in example_specs:
    group = _faq_example(comment_id)
    first = group.iloc[0]
    mappings = tuple(f"{str(row.aspect).replace('_', ' ').title()} → {str(row.sentiment).replace('_', ' ').title()}" for row in group[["aspect", "sentiment"]].drop_duplicates().itertuples(index=False))
    with st.expander(f"{label}: {title}", expanded=False):
        render_example_card(label=label, title=str(first["post_title"]), comment=str(first["comment_text"]), explanation=explanation, mappings=mappings, url=str(first["post_url"]))

comparison_rows = voc_examples.loc[voc_examples["comment_unit_id"].eq("comment_0007375")].copy()
if comparison_rows.empty:
    raise DataContractError("Frozen comparative FAQ example is unavailable")
comparison = comparison_rows.iloc[0]
with st.expander("Comparative multi-brand comment: one comment can support more than one brand", expanded=False):
    render_example_card(
        label="Cross-brand comparison",
        title="Amex and Chase are both explicit",
        comment=str(comparison["display_text"]),
        explanation="This approved excerpt explicitly discusses both Amex and Chase. Each supported proposition can contribute to its relevant brand view without duplicating the comment inside the same brand-theme view.",
        mappings=("Amex → Reservation experience → Mixed / neutral", "Chase → Overall lounge experience → Mixed / neutral"),
        url=str(comparison["post_url"]),
    )

_section("glossary", "Plain-English glossary")
glossary = (
    ("Comment", "One individual Reddit response used as the primary executive counting unit."),
    ("Observation", "One supported brand/lounge × detailed experience area × sentiment proposition."),
    ("Experience-bearing", "A comment that communicates a direct, second-hand or broader experience-grounded lounge opinion."),
    ("Usable comment", "An experience-bearing comment specific enough for reliable detailed analysis."),
    ("General Lounge Experience", "The overall impression of a lounge, kept separate from operational experience areas."),
    ("Executive theme", "One of five presentation groups that organizes detailed experience areas without changing them."),
    ("Detailed aspect", "The original specific experience area assigned during extraction."),
    ("Title-resolved", "Context safely clarified from a thread title containing one clear target."),
    ("UNKNOWN", "An intentionally unresolved brand, lounge or airport assignment used when evidence is insufficient."),
    ("Sampled peer", "Another brand with enough eligible evidence for the specific comparison."),
    ("Head-to-head", "A same-airport comparison where exactly one qualifying peer is available."),
    ("Mixed / neutral", "Executive grouping for mixed evidence and neutral-only outcomes."),
    ("95% estimate range", "A repeated-sample uncertainty interval; narrower generally means more precise."),
    ("Source robustness", "Whether a result remains directionally similar across different Reddit community groups."),
)
render_glossary(glossary)
st.caption("All methodology values and examples are loaded from frozen local files. No runtime LLM or external API is used.")

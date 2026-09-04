"""Display constants and controlled vocabulary for the dashboard."""

from pathlib import Path


DASHBOARD_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DASHBOARD_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "dashboard"

SCOPE_LABEL = "Jan–Aug 2026"
SCOPE_BADGE = "2026 YTD"

HEADLINE_ISSUERS = ("AMEX", "CHASE", "CAPITAL_ONE", "DELTA")

ENTITY_DISPLAY_NAMES = {
    "AMEX": "American Express",
    "CHASE": "Chase",
    "CAPITAL_ONE": "Capital One",
    "DELTA": "Delta",
    "CENTURION": "Centurion Lounge",
    "SAPPHIRE_LOUNGE": "Sapphire Lounge",
    "CAPITAL_ONE_LOUNGE": "Capital One Lounge",
    "CAPITAL_ONE_LANDING": "Capital One Landing",
    "PRIORITY_PASS": "Priority Pass",
    "ESCAPE_LOUNGE": "Escape Lounge",
    "PLAZA_PREMIUM": "Plaza Premium",
    "DELTA_SKY_CLUB": "Delta Sky Club",
}

ENTITY_SHORT_NAMES = {
    "AMEX": "Amex",
    "CHASE": "Chase",
    "CAPITAL_ONE": "Capital One",
    "DELTA": "Delta",
    "CENTURION": "Centurion",
    "SAPPHIRE_LOUNGE": "Sapphire Lounge",
    "CAPITAL_ONE_LOUNGE": "Capital One Lounge",
    "CAPITAL_ONE_LANDING": "Capital One Landing",
    "PRIORITY_PASS": "Priority Pass",
    "ESCAPE_LOUNGE": "Escape Lounge",
    "PLAZA_PREMIUM": "Plaza Premium",
    "DELTA_SKY_CLUB": "Delta Sky Club",
}

# These colors identify entities in multi-series charts. They never encode sentiment.
ENTITY_COLORS = {
    "AMEX": "#246BFD",
    "CHASE": "#6C5CE7",
    "CAPITAL_ONE": "#D54B58",
    "DELTA": "#5C6F91",
    "CENTURION": "#2F75B5",
    "SAPPHIRE_LOUNGE": "#3155A6",
    "CAPITAL_ONE_LOUNGE": "#B83D4A",
    "CAPITAL_ONE_LANDING": "#9B4458",
    "PRIORITY_PASS": "#6E4B8B",
    "ESCAPE_LOUNGE": "#2F7D72",
    "PLAZA_PREMIUM": "#9A6A33",
    "DELTA_SKY_CLUB": "#59677F",
}

HEADLINE_NETWORKS = (
    "CENTURION",
    "SAPPHIRE_LOUNGE",
    "CAPITAL_ONE_LOUNGE",
    "CAPITAL_ONE_LANDING",
    "PRIORITY_PASS",
    "ESCAPE_LOUNGE",
    "PLAZA_PREMIUM",
    "DELTA_SKY_CLUB",
)

SOURCE_BUCKET_DISPLAY_NAMES = {
    "ALL": "All sources",
    "HOME_BRAND_COMMUNITY": "Home brand community",
    "GENERAL_COMMUNITY": "General community",
    "OTHER_COMMUNITY": "Non-home / other community",
}

METRIC_DISPLAY_NAMES = {
    "OVERALL_EXPERIENCE": "Overall Experience Sentiment",
    "ATTRIBUTE_INDEX": "Attribute Experience Index",
}

METRIC_HELP_TEXT = {
    "OVERALL_EXPERIENCE": "Uses only explicit evaluations of the lounge overall.",
    "ATTRIBUTE_INDEX": "Comment-weighted summary of specific product and operational aspects, excluding Overall Experience.",
}

CONFIDENCE_ORDER = ("HIGH", "MEDIUM", "LOW", "VERY_LOW")

CONFIDENCE_DISPLAY_NAMES = {
    "HIGH": "High confidence",
    "MEDIUM": "Medium confidence",
    "LOW": "Limited sample",
    "VERY_LOW": "Very limited sample",
}

CONFIDENCE_HELP_TEXT = {
    "HIGH": "The result has the strongest available sample support for executive use.",
    "MEDIUM": "The result has sufficient support for executive use with normal context.",
    "LOW": "The sample is limited; treat the result as directional and do not use it as a headline conclusion.",
    "VERY_LOW": "The sample is very limited; the result is de-emphasized and should be interpreted cautiously.",
}

ROBUSTNESS_DISPLAY_NAMES = {
    "ROBUST_ACROSS_SOURCES": "Consistent across sources",
    "DIRECTION_ROBUST_MAGNITUDE_SENSITIVE": "Same direction across sources",
    "SOURCE_SENSITIVE": "Varies by source",
    "INSUFFICIENT_CROSS_SOURCE_SAMPLE": "Limited source coverage",
}

ROBUSTNESS_HELP_TEXT = {
    "ROBUST_ACROSS_SOURCES": "Direction and magnitude are similar across the source groups with enough data.",
    "DIRECTION_ROBUST_MAGNITUDE_SENSITIVE": "The result stays positive or negative across sources, but the size of the result varies meaningfully.",
    "SOURCE_SENSITIVE": "The conclusion changes depending on which source communities are included. Interpret with caution.",
    "INSUFFICIENT_CROSS_SOURCE_SAMPLE": "There is not enough data across multiple source groups to assess robustness reliably.",
}

ROBUSTNESS_TONES = {
    "ROBUST_ACROSS_SOURCES": "positive",
    "DIRECTION_ROBUST_MAGNITUDE_SENSITIVE": "neutral",
    "SOURCE_SENSITIVE": "caution",
    "INSUFFICIENT_CROSS_SOURCE_SAMPLE": "muted",
}

EXECUTIVE_POSITION_DISPLAY_NAMES = {
    "TRUE_STRENGTH": "Clear competitive strength",
    "TRUE_WEAKNESS": "Clear competitive weakness",
    "LESS_BAD_THAN_PEERS": "Better than peers, but still negative",
    "GOOD_BUT_BEHIND_PEERS": "Positive, but trails peers",
    "PEER_PARITY": "In line with peers",
    "MIXED_POSITION": "Mixed position",
}

EXECUTIVE_POSITION_HELP_TEXT = {
    "TRUE_STRENGTH": "Absolute customer experience is positive and performance is ahead of sampled peers.",
    "TRUE_WEAKNESS": "Absolute customer experience is negative and performance trails sampled peers.",
    "LESS_BAD_THAN_PEERS": "This metric is less negative than sampled peers, but the absolute customer experience is still negative.",
    "GOOD_BUT_BEHIND_PEERS": "Absolute customer experience is positive, but performance trails sampled peers.",
    "PEER_PARITY": "Performance is broadly in line with sampled peers.",
    "MIXED_POSITION": "Absolute and relative signals do not support a simple strength or weakness conclusion.",
}

EXECUTIVE_POSITION_TONES = {
    "TRUE_STRENGTH": "positive",
    "TRUE_WEAKNESS": "negative",
    "LESS_BAD_THAN_PEERS": "caution",
    "GOOD_BUT_BEHIND_PEERS": "caution",
    "PEER_PARITY": "neutral",
    "MIXED_POSITION": "caution",
}

ATTRIBUTION_DISPLAY_NAMES = {
    "HIGH_SENSITIVITY": "Attribution-sensitive",
    "MODERATE_SENSITIVITY": "Some attribution sensitivity",
    "STABLE": "Stable attribution",
}

ATTRIBUTION_HELP_TEXT = {
    "HIGH_SENSITIVITY": "The primary and title-resolved sensitivity analyses differ materially for this period.",
    "MODERATE_SENSITIVITY": "The primary and title-resolved sensitivity analyses differ moderately for this period.",
    "STABLE": "The primary and title-resolved sensitivity analyses are broadly aligned for this period.",
}

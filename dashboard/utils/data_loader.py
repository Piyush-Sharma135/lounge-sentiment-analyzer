"""Centralized, cached access to frozen canonical dashboard CSVs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from utils.constants import DATA_DIR


CONTRACT_FILE = DATA_DIR / "58_public_runtime_contract.csv"
HOME_FROZEN_SUMMARY_FILE = DATA_DIR / "58_home_frozen_summary.csv"
FINAL_ANALYSIS_FREEZE_FILE = DATA_DIR / "55_v4_final_analysis_freeze.csv"

PRESENTATION_FILES = {
    "EXECUTIVE_BRAND_COMMENTS": "56_executive_brand_comment_summary.csv",
    "EXECUTIVE_THEME_BRANDS": "56_executive_theme_brand_summary.csv",
    "EXECUTIVE_THEME_MONTHLY": "56_executive_theme_monthly.csv",
    "EXECUTIVE_PRESENTATION_QA": "56_executive_presentation_qa.csv",
    "EXECUTIVE_INSIGHTS": "59_executive_insights.csv",
    "EXECUTIVE_INSIGHT_QA": "59_executive_insight_qa.csv",
    "AIRPORT_DYNAMIC_INSIGHTS": "60_airport_dynamic_insights.csv",
    "AIRPORT_DYNAMIC_INSIGHT_QA": "60_airport_dynamic_insight_qa.csv",
    "AIRPORT_REPRESENTATIVE_COMMENTS": "61_airport_representative_comments.csv",
    "AIRPORT_REPRESENTATIVE_COMMENT_QA": "61_airport_representative_comment_qa.csv",
}


@st.cache_data(show_spinner=False)
def _read_csv(path_text: str, modified_ns: int) -> pd.DataFrame:
    """Read a CSV, with file modification time included in the cache key."""
    del modified_ns
    return pd.read_csv(path_text)


def load_csv(path: Path) -> pd.DataFrame:
    """Load a local CSV through the shared cache."""
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Dashboard data file not found: {resolved}")
    return _read_csv(str(resolved), resolved.stat().st_mtime_ns)


def load_canonical_contract() -> pd.DataFrame:
    """Load the V4 canonical dashboard contract."""
    return load_csv(CONTRACT_FILE)


def canonical_file_for(dataset_role: str) -> Path:
    """Resolve a dataset role through the canonical contract, never an older version."""
    contract = load_canonical_contract()
    matches = contract.loc[
        contract["dataset_role"].astype(str).str.upper() == dataset_role.upper(),
        "canonical_file",
    ]
    if matches.empty:
        raise KeyError(f"Unknown canonical dashboard dataset role: {dataset_role}")
    if len(matches) > 1:
        raise ValueError(f"Duplicate canonical contract rows for role: {dataset_role}")
    return DATA_DIR / str(matches.iloc[0])


def load_canonical_dataset(dataset_role: str) -> pd.DataFrame:
    """Load a contracted dashboard dataset by semantic role."""
    return load_csv(canonical_file_for(dataset_role))


def load_presentation_dataset(dataset_role: str) -> pd.DataFrame:
    """Load an offline-built executive presentation table.

    Presentation tables contain approved comment-level aggregations. Keeping
    this lookup separate from the frozen analytical contract makes their role
    explicit and prevents Streamlit pages from rebuilding them at runtime.
    """
    try:
        filename = PRESENTATION_FILES[dataset_role.upper()]
    except KeyError as error:
        raise KeyError(
            f"Unknown executive presentation dataset role: {dataset_role}"
        ) from error
    return load_csv(DATA_DIR / filename)


def load_home_frozen_summaries() -> dict[str, pd.DataFrame]:
    """Load public aggregate summaries used to verify Home headline counts."""
    summary = load_csv(HOME_FROZEN_SUMMARY_FILE)
    required = {"summary_group", "metric", "value"}
    missing = sorted(required - set(summary.columns))
    if missing:
        raise ValueError(f"Public frozen summary is missing columns: {missing}")

    def rows(group: str) -> pd.DataFrame:
        selected = summary.loc[
            summary["summary_group"].eq(group), ["metric", "value"]
        ].copy()
        if selected.empty:
            raise ValueError(f"Public frozen summary is missing group: {group}")
        return selected

    return {
        "production_population": rows("production_population"),
        "stage2a1": rows("stage2a1"),
        "stage2b_population": rows("stage2b_population"),
        "stage2b_freeze": rows("stage2b_freeze"),
        "final_analysis_freeze": load_csv(FINAL_ANALYSIS_FREEZE_FILE),
    }

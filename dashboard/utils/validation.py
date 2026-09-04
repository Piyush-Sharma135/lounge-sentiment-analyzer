"""Lightweight canonical data-contract validation."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


class DataContractError(ValueError):
    """Raised when a canonical dashboard dataset violates an expected contract."""


def require_columns(
    frame: pd.DataFrame,
    required: Iterable[str],
    dataset_name: str,
) -> None:
    """Require a set of columns before presentation logic runs."""
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        joined = ", ".join(missing)
        raise DataContractError(f"{dataset_name} is missing required columns: {joined}")


def require_values(
    frame: pd.DataFrame,
    column: str,
    expected: Iterable[str],
    dataset_name: str,
) -> None:
    """Require controlled values to be represented in a dataset."""
    require_columns(frame, [column], dataset_name)
    available = set(frame[column].dropna().astype(str))
    missing = sorted(set(expected) - available)
    if missing:
        joined = ", ".join(missing)
        raise DataContractError(
            f"{dataset_name} has no rows for required {column} values: {joined}"
        )


def require_unique(
    frame: pd.DataFrame,
    columns: Iterable[str],
    dataset_name: str,
) -> None:
    """Require one canonical row per presentation key."""
    keys = list(columns)
    require_columns(frame, keys, dataset_name)
    duplicate_rows = frame.loc[frame.duplicated(keys, keep=False), keys]
    if not duplicate_rows.empty:
        examples = duplicate_rows.drop_duplicates().head(3).to_dict("records")
        raise DataContractError(
            f"{dataset_name} contains duplicate rows for {keys}. Examples: {examples}"
        )

"""Helpers for safely passing custom HTML through Streamlit Markdown."""

from __future__ import annotations


def compact_html(markup: str) -> str:
    """Remove Markdown-significant indentation from trusted HTML markup."""
    return " ".join(line.strip() for line in markup.splitlines() if line.strip())

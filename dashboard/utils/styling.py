"""Local styling loader for the Streamlit shell."""

from pathlib import Path

import streamlit as st


STYLE_DIR = Path(__file__).resolve().parents[1] / "assets" / "styles"
STYLE_FILES = (
    STYLE_DIR / "base.css",
    STYLE_DIR / "executive_overview.css",
)


def apply_base_styles() -> None:
    """Inject the local dashboard stylesheet."""
    missing = [path for path in STYLE_FILES if not path.is_file()]
    if missing:
        st.warning(f"Dashboard stylesheet is missing: {missing[0]}")
        return
    css = "\n".join(path.read_text(encoding="utf-8") for path in STYLE_FILES)
    st.html(f'<span id="dashboard-style-anchor" hidden></span><style>{css}</style>')

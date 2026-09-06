"""Local styling loader for the Streamlit shell."""

from pathlib import Path

import streamlit as st

from utils.assets import STATIC_DIR


STYLE_DIR = Path(__file__).resolve().parents[1] / "assets" / "styles"
STYLE_FILES = (
    STYLE_DIR / "base.css",
    STYLE_DIR / "executive_overview.css",
)


def apply_base_styles() -> None:
    """Inject the local dashboard stylesheet."""
    image_files = {
        "__EXECUTIVE_HERO_IMAGE__": STATIC_DIR / "executive-lounge-hero.png",
        "__EXECUTIVE_BACKGROUND_IMAGE__": STATIC_DIR
        / "executive-dashboard-background.png",
    }
    image_urls = {
        "__EXECUTIVE_HERO_IMAGE__": "/app/static/executive-lounge-hero.png",
        "__EXECUTIVE_BACKGROUND_IMAGE__": "/app/static/executive-dashboard-background.png",
    }
    missing = [
        path for path in (*STYLE_FILES, *image_files.values()) if not path.is_file()
    ]
    if missing:
        st.warning(f"Dashboard visual asset is missing: {missing[0]}")
        return
    css = "\n".join(path.read_text(encoding="utf-8") for path in STYLE_FILES)
    for placeholder, url in image_urls.items():
        css = css.replace(placeholder, url)
    st.html(f'<span id="dashboard-style-anchor" hidden></span><style>{css}</style>')

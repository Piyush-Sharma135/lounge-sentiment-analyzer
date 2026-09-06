"""Local visual-asset helpers for the public dashboard runtime."""

from __future__ import annotations

import base64
from functools import lru_cache
from html import escape
from pathlib import Path


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
IMAGE_DIR = ASSET_DIR / "images"
BRAND_DIR = ASSET_DIR / "brands"

BRAND_MARKS = {
    "AMEX": ("american-express.svg", "American Express"),
    "CHASE": ("chase.svg", "Chase"),
    "CAPITAL_ONE": ("capital-one.svg", "Capital One"),
    "DELTA": ("delta.svg", "Delta"),
}


@lru_cache(maxsize=None)
def asset_data_uri(path: Path) -> str:
    """Return a cached data URI so visual assets remain fully local at runtime."""
    suffix = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix)
    if mime is None:
        raise ValueError(f"Unsupported dashboard asset type: {path.name}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def brand_logo_img(brand: str) -> str:
    """Render a decorative local brand mark beside an existing text label."""
    asset = BRAND_MARKS.get(brand)
    if asset is None:
        return ""
    filename, label = asset
    slug = brand.lower().replace("_", "-")
    return (
        f'<img class="brand-logo brand-logo-{escape(slug)}" '
        f'src="{asset_data_uri(BRAND_DIR / filename)}" '
        f'alt="" aria-hidden="true" title="{escape(label)}">'
    )

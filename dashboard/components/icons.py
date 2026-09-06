"""Small dependency-free SVG icon system for executive presentation cues."""

from __future__ import annotations

from html import escape


ICON_MARKUP = {
    "compass": '<circle cx="12" cy="12" r="8.5"/><path d="m15.4 8.6-2.1 4.7-4.7 2.1 2.1-4.7 4.7-2.1Z"/>',
    "data": '<path d="M4 19V9m6 10V5m6 14v-7m5 7H2"/>',
    "themes": '<rect x="3.5" y="3.5" width="6.5" height="6.5" rx="1.2"/><rect x="14" y="3.5" width="6.5" height="6.5" rx="1.2"/><rect x="3.5" y="14" width="6.5" height="6.5" rx="1.2"/><rect x="14" y="14" width="6.5" height="6.5" rx="1.2"/>',
    "guide": '<path d="M4 5.5c3.1-.8 5.7-.2 8 1.6v12c-2.3-1.8-4.9-2.4-8-1.6v-12Zm16 0c-3.1-.8-5.7-.2-8 1.6v12c2.3-1.8 4.9-2.4 8-1.6v-12Z"/>',
    "brands": '<path d="M4 20V8l8-4v16M12 10h8v10M2 20h20M7 11h2m-2 4h2m7-1h1"/>',
    "community": '<path d="M5 16.5 3.5 20l4-1.8c1.1.5 2.4.8 3.8.8 4.2 0 7.7-2.7 7.7-6s-3.5-6-7.7-6S3.5 9.7 3.5 13c0 1.3.5 2.5 1.5 3.5Z"/><path d="M15.8 6.8c.5-.1 1-.1 1.5-.1 2.8 0 5.2 1.7 5.2 3.9 0 1-.5 2-1.3 2.7l.8 2.3-2.7-1.2"/>',
    "performance": '<path d="M4 19V9m6 10V5m6 14v-7m5 7H2"/><path d="m4 7 5-4 5 4 6-5"/>',
    "drivers": '<path d="M4 5h9m4 0h3M4 12h3m4 0h9M4 19h8m4 0h4"/><circle cx="15" cy="5" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="14" cy="19" r="2"/>',
    "trend": '<path d="M3 17.5 8.5 12l4 3.5L21 7"/><path d="M15.5 7H21v5.5"/>',
    "airport": '<path d="m3 13 7.2-1.7V5.5a1.8 1.8 0 0 1 3.6 0v5.8L21 13v2l-7.2-.8v4l2.2 1.4V21l-4-1-4 1v-1.4l2.2-1.4v-4L3 15v-2Z"/>',
    "explore": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.2 15.2 5.3 5.3M10.5 7.5v6m-3-3h6"/>',
    "location": '<path d="M12 21s6-5.8 6-11a6 6 0 1 0-12 0c0 5.2 6 11 6 11Z"/><circle cx="12" cy="10" r="2.2"/>',
    "attention": '<path d="M12 3 2.8 20h18.4L12 3Z"/><path d="M12 9v5m0 3h.01"/>',
    "positive": '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.6 2.6L16.5 9"/>',
    "negative": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6m0-6-6 6"/>',
    "compare": '<path d="M4 7h14m-3-3 3 3-3 3M20 17H6m3 3-3-3 3-3"/>',
    "map": '<path d="m3.5 6 5-2 7 2 5-2v14l-5 2-7-2-5 2V6Z"/><path d="M8.5 4v14m7-12v14"/>',
    "filter": '<path d="M3 5h18l-7 8v5l-4 2v-7L3 5Z"/>',
    "mixed": '<path d="M12 4v16M5 7h14M7 7l-3 6h6L7 7Zm10 0-3 6h6l-3-6Z"/><path d="M8 20h8"/>',
    "general": '<path d="m12 3 2.5 5.3 5.7.8-4.1 4.1 1 5.8-5.1-2.7L6.9 19l1-5.8-4.1-4.1 5.7-.8L12 3Z"/>',
    "capacity": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.2"/><path d="M3.5 20v-2.2A4.8 4.8 0 0 1 8.3 13h1.4a4.8 4.8 0 0 1 4.8 4.8V20M15 14h1.5a4 4 0 0 1 4 4v2"/>',
    "food": '<path d="M7 3v7m-2-7v4a2 2 0 0 0 4 0V3m-2 7v11M16 3v18m0-18c3 2 4 5.2 0 8"/>',
    "service": '<path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3Zm6 10 .8 2.2L21 16l-2.2.8L18 19l-.8-2.2L15 16l2.2-.8L18 13ZM6 14l.8 2.2L9 17l-2.2.8L6 20l-.8-2.2L3 17l2.2-.8L6 14Z"/>',
    "amenities": '<path d="M4 13h16v6H4v-6Zm2-5h12a2 2 0 0 1 2 2v3H4v-3a2 2 0 0 1 2-2Zm0 11v2m12-2v2"/><path d="M9 5.5a4.5 4.5 0 0 1 6 0M10.8 7.2a2 2 0 0 1 2.4 0"/>',
    "scope": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>',
    "attribution": '<path d="M9.5 14.5 8 16a4 4 0 0 1-5.7-5.7l3-3A4 4 0 0 1 11 7m3.5 2.5L16 8a4 4 0 0 1 5.7 5.7l-3 3A4 4 0 0 1 13 17"/><path d="m8.5 15.5 7-7"/>',
}

TITLE_ICONS = {
    "Where do you want to start?": "compass",
    "About the data": "data",
    "What parts of the lounge experience are analyzed?": "themes",
    "How to read the numbers": "guide",
    "Brands covered": "brands",
    "Where the conversation comes from": "community",
    "Brand Performance Overview": "performance",
    "Experience Drivers": "drivers",
    "Trend & Momentum": "trend",
    "Airport Overview": "airport",
    "Explore Airports by Brand": "explore",
    "Airport-Level Performance": "performance",
    "Airports needing attention": "attention",
    "Airports performing well": "positive",
    "Where brands can be compared directly": "compare",
    "Airport Signal Map": "map",
    "Explore Customer Voices": "filter",
    "Positive Voices": "positive",
    "Negative Voices": "negative",
    "Mixed / Nuanced Voices": "mixed",
    "Compare Customer Voices": "compare",
    "Analysis Scope & Approach": "scope",
    "What Counts as Lounge Feedback": "filter",
    "Brand, Lounge & Airport Attribution": "attribution",
    "Experience Theme Framework": "themes",
    "Sentiment & Comment Counting": "data",
    "How to Read the Results": "guide",
}

THEME_ICONS = {
    "General Lounge Experience": "general",
    "Access & Capacity": "capacity",
    "Food & Beverage": "food",
    "Service & Upkeep": "service",
    "Space, Amenities & Convenience": "amenities",
}


def icon_svg(name: str, *, css_class: str = "ui-icon") -> str:
    """Return a compact, accessible decorative SVG from the local icon set."""
    markup = ICON_MARKUP.get(name, ICON_MARKUP["themes"])
    return (
        f'<svg class="{escape(css_class)}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false">{markup}</svg>'
    )


def title_icon_svg(title: str, *, css_class: str = "ui-icon") -> str:
    return icon_svg(TITLE_ICONS.get(title, "themes"), css_class=css_class)


def theme_icon_svg(theme: str, *, css_class: str = "ui-icon") -> str:
    return icon_svg(THEME_ICONS.get(theme, "themes"), css_class=css_class)

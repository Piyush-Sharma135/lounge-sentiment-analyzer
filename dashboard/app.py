"""Streamlit entry point for the Reddit Lounge Intelligence dashboard."""

from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="Reddit Lounge Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.html import compact_html  # noqa: E402
from utils.styling import apply_base_styles  # noqa: E402


APP_DIR = Path(__file__).resolve().parent

apply_base_styles()

pages = {
    "Executive intelligence": [
        st.Page(
            APP_DIR / "pages" / "00_home.py",
            title="Home",
            icon="🏠",
            default=True,
        ),
        st.Page(
            APP_DIR / "pages" / "01_executive_overview.py",
            title="Executive Overview",
            icon="📊",
        ),
        st.Page(
            APP_DIR / "pages" / "04_airport_explorer.py",
            title="Airport View",
            icon="✈️",
        ),
        st.Page(
            APP_DIR / "pages" / "06_voice_of_customer.py",
            title="Voice of Customer",
            icon="💬",
        ),
    ],
    "Evidence & methodology": [
        st.Page(
            APP_DIR / "pages" / "07_methodology_faq.py",
            title="FAQ / Methodology",
            icon="ℹ️",
        ),
    ],
}

with st.sidebar:
    st.markdown(
        compact_html(
            """
        <div class="sidebar-brand">
            <span class="sidebar-kicker">2026 YTD</span>
            <div class="sidebar-title">Lounge Intelligence</div>
            <div class="sidebar-subtitle">Reddit directional voice of customer</div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )

navigation = st.navigation(pages, position="sidebar", expanded=True)
navigation.run()

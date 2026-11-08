import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components


# -----------------------------------------------------------------------------
# Streamlit page setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ABC123",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
#MainMenu, footer, header,
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], .stDeployButton,
[data-testid="stSidebar"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[class*="viewerBadge"], [class*="profileContainer"], [class*="profilePreview"],
a[href*="streamlit.io"] {
  display: none !important;
  visibility: hidden !important;
}
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
section.main, .main {
  background: #070b18 !important;
  overflow: hidden !important;
}
.block-container, [data-testid="stMainBlockContainer"] {
  padding: 0 !important;
  margin: 0 !important;
  max-width: none !important;
}
iframe {
  position: fixed !important;
  inset: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  height: 100dvh !important;
  border: 0 !important;
  margin: 0 !important;
  z-index: 2147483000 !important;
  background: transparent !important;
}
[data-stale], [data-stale="true"] {
  opacity: 1 !important;
  transition: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Frontend Streamlit component
# -----------------------------------------------------------------------------
FRONTEND = (Path(__file__).parent / "frontend").resolve()
if not (FRONTEND / "index.html").is_file():
    st.error(
        f"Missing {FRONTEND / 'index.html'}. "
        "Commit the complete frontend folder to your repository."
    )
    st.stop()

ascent_ui = components.declare_component("ascent_ui", path=str(FRONTEND))


# -----------------------------------------------------------------------------
# Cloudflare Workers AI — Google Gemma 4 26B A4B
# -----------------------------------------------------------------------------
MODEL = "@cf/google/gemma-4-26b-a4b-it"
DEFAULT_CLOUDFLARE_ENDPOINT = "https://api.cloudflare.com/client/v4"
SYSTEM_PROMPT = (
    "You are a helpful, clear, and accurate AI assistant. "
    "When the user attaches an image, inspect it and answer questions about its contents. "
    "If something in an image is unclear, say so instead of guessing."
)


def secret(name: str, default: str = "") -> str:
    """Read Streamlit Secrets first, then environment variables."""
    try:
        value = st.secrets[name]
    except Exception:
        value = None
    return str(value or os.environ.get(name, default)).strip()

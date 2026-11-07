import os
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Ascent",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------- hide all Streamlit UI
st.markdown(
    """
<style>
#MainMenu, footer, header,
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], .stDeployButton,
[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"]
{ display: none !important; visibility: hidden !important; }

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main, .main
{ background: #070b18 !important; overflow: hidden !important; }

.block-container, [data-testid="stMainBlockContainer"]
{ padding: 0 !important; margin: 0 !important; max-width: none !important; }

/* the Ascent interface fills the whole window */
iframe {
  position: fixed !important; inset: 0 !important;
  width: 100vw !important; height: 100vh !important; height: 100dvh !important;
  border: 0 !important; margin: 0 !important; z-index: 2147483000 !important;
  background: transparent !important;
}

/* never dim the interface while Python is working */
[data-stale], [data-stale="true"] { opacity: 1 !important; transition: none !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- the interface (frontend/index.html)
FRONTEND = (Path(__file__).parent / "frontend").resolve()
if not (FRONTEND / "index.html").is_file():
    st.error(f"Missing {FRONTEND / 'index.html'}. Commit the whole 'frontend' folder to your repo.")
    st.stop()

ascent_ui = components.declare_component("ascent_ui", path=str(FRONTEND))


# ---------------------------------------------------------------- Ollama
def secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets[name]
    except Exception:
        value = None
    return str(value or os.environ.get(name, default))


def ollama_chat(messages: list) -> str:
    key = secret("OLLAMA_API_KEY")
    if not key:
        raise RuntimeError("OLLAMA_API_KEY is not set in Streamlit secrets.")
    host = secret("OLLAMA_HOST", "https://ollama.com").rstrip("/")
    model = secret("OLLAMA_MODEL", "gemma4")

    clean = []
    for m in messages:
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant", "system"):
            continue
        item = {"role": m["role"], "content": str(m.get("content", ""))}
        if m.get("images"):
            item["images"] = [str(i) for i in m["images"]]
        clean.append(item)
    if not clean:
        raise RuntimeError("Empty conversation.")

    r = requests.post(
        f"{host}/api/chat",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": clean, "stream": False},
        timeout=300,
    )
    if not r.ok:
        raise RuntimeError(r.text[:400] or f"Ollama returned HTTP {r.status_code}")
    return (r.json().get("message") or {}).get("content", "")


# ---------------------------------------------------------------- glue
st.session_state.setdefault("reply", None)
st.session_state.setdefault("handled", None)

value = ascent_ui(reply=st.session_state.reply, key="ascent", default=None)

if isinstance(value, dict) and value.get("id") and value["id"] != st.session_state.handled:
    st.session_state.handled = value["id"]
    try:
        st.session_state.reply = {"id": value["id"], "text": ollama_chat(value.get("messages") or [])}
    except Exception as e:  # shown inside the Ascent interface as an error bubble
        st.session_state.reply = {"id": value["id"], "error": str(e)}
    st.rerun()

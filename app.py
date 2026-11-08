import os
import sys
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="ABC123",
    page_icon="🍕",
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
[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"],
[class*="viewerBadge"], [class*="profileContainer"], [class*="profilePreview"], a[href*="streamlit.io"]
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


# ---------------------------------------------------------------- Ollama Cloud
OLLAMA_HOST = "https://ollama.com"
# Ollama's docs call the hosted model "muse-spark-open"; "muse-spark-open:cloud" is the CLI name.
# Try the API name first and fall back to the CLI name if the server doesn't know it.
MODEL_NAMES = ["muse-spark-open", "muse-spark-open:cloud"]

# CACHING: Ollama Cloud caches the processed start of a prompt automatically, and bills those
# repeated tokens at the lower "cached" rate. A cache hit needs the start of every request to be
# IDENTICAL to the previous one, so this file never changes it:
#   1. the system prompt is one fixed string (no dates, names or anything that varies),
#   2. the chat history is sent in the same order and unchanged, only new messages are added at the end,
#   3. the model name and settings below are the same on every request.
SYSTEM_PROMPT = (
    "You are a helpful, accurate AI assistant. "
    "You can analyze uploaded images directly. "
    "Answer questions about their contents."
)
OPTIONS = {"temperature": 0.6, "num_predict": 4096}


def secret(name: str, default: str = "") -> str:
    """Read a value from Streamlit Secrets first, then environment variables."""
    try:
        value = st.secrets[name]
    except Exception:
        value = None
    return str(value or os.environ.get(name, default)).strip()


def ollama_chat(messages: list) -> dict:
    """Send the conversation (text and images) to Muse Spark Open on Ollama Cloud."""
    api_key = secret("OLLAMA_API_KEY")
    if not api_key:
        raise RuntimeError("Ollama Cloud is not configured. Add OLLAMA_API_KEY to Streamlit Secrets.")

    # Fixed system prompt first (cache-friendly). A system message from the browser is ignored.
    clean = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            continue
        item = {"role": message["role"], "content": str(message.get("content", "") or "")}
        images = [
            image.split(",", 1)[-1] if image.startswith("data:") else image
            for image in (message.get("images") or [])
            if isinstance(image, str) and image
        ]
        if item["role"] == "user" and images:
            item["images"] = images  # raw base64, unchanged on every turn so the cached prefix stays valid
        clean.append(item)
    if len(clean) == 1:
        raise RuntimeError("The conversation is empty.")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = None
    for index, model in enumerate(MODEL_NAMES):
        body = {"model": model, "messages": clean, "stream": False, "options": OPTIONS}
        try:
            response = requests.post(f"{OLLAMA_HOST}/api/chat", headers=headers, json=body, timeout=300)
        except requests.RequestException as exc:
            raise RuntimeError(f"Could not reach Ollama Cloud: {exc}") from exc
        if response.status_code == 404 and index < len(MODEL_NAMES) - 1:
            continue
        break

    if not response.ok:
        detail = response.text[:500]
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("error"):
                detail = str(payload["error"])
        except ValueError:
            pass
        if response.status_code in (401, 403):
            detail = f"Ollama rejected the API key ({detail})"
        raise RuntimeError(f"Ollama Cloud HTTP {response.status_code}: {detail}")

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"Invalid Ollama response: {response.text[:300]}")

    message = data.get("message") or {}
    answer = str(message.get("content") or "").strip()
    thinking = str(message.get("thinking") or message.get("reasoning") or "").strip()

    # Token counts go to the app log so you can check that later turns are cheaper/faster.
    print(
        f"[ollama] prompt_tokens={data.get('prompt_eval_count')} "
        f"output_tokens={data.get('eval_count')} prompt_ms={(data.get('prompt_eval_duration') or 0) // 1_000_000}",
        file=sys.stderr, flush=True,
    )

    if not answer:
        raise RuntimeError(
            "The model returned an empty reply (it may have used its whole token limit while thinking). "
            "Try again or ask something shorter."
        )
    return {"text": answer, "thinking": thinking}


# ---------------------------------------------------------------- Streamlit component bridge
st.session_state.setdefault("reply", None)
st.session_state.setdefault("handled", None)

value = ascent_ui(reply=st.session_state.reply, key="ascent", default=None)

if isinstance(value, dict) and value.get("id") and value["id"] != st.session_state.handled:
    st.session_state.handled = value["id"]
    try:
        result = ollama_chat(value.get("messages") or [])
        st.session_state.reply = {"id": value["id"], **result}
    except Exception as exc:  # shown inside the interface as an error bubble
        st.session_state.reply = {"id": value["id"], "error": str(exc)}
    st.rerun()

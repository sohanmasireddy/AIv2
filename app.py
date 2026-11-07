import hashlib
import os
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


# ---------------------------------------------------------------- Cloudflare credentials and API helpers
def secret(name: str, default: str = "") -> str:
    """Read a value from Streamlit Secrets first, then environment variables."""
    try:
        value = st.secrets[name]
    except Exception:
        value = None
    return str(value or os.environ.get(name, default)).strip()


def cloudflare_credentials() -> tuple[str, str]:
    account_id = secret("CLOUDFLARE_ACCOUNT_ID")
    # Support both names used in Cloudflare examples and older deployments.
    api_token = secret("CLOUDFLARE_API_TOKEN") or secret("CLOUDFLARE_AUTH_TOKEN")
    if not account_id or not api_token:
        raise RuntimeError(
            "Cloudflare is not configured. Add CLOUDFLARE_ACCOUNT_ID and "
            "CLOUDFLARE_API_TOKEN to Streamlit Secrets."
        )
    return account_id, api_token


def cloudflare_run(model: str, inputs: dict, timeout: int = 300) -> dict:
    """Call one Cloudflare Workers AI model through its account REST endpoint."""
    account_id, api_token = cloudflare_credentials()
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/{model}"
    )
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json=inputs,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach Cloudflare Workers AI: {exc}") from exc

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if not response.ok:
        detail = ""
        if isinstance(payload, dict):
            errors = payload.get("errors") or []
            if errors:
                detail = "; ".join(
                    str(item.get("message", item)) if isinstance(item, dict) else str(item)
                    for item in errors
                )
        if not detail:
            detail = response.text[:900] or f"HTTP {response.status_code}"
        raise RuntimeError(f"Cloudflare returned HTTP {response.status_code}: {detail}")

    if not isinstance(payload, dict):
        raise RuntimeError("Cloudflare returned an unexpected response format.")

    if payload.get("success") is False:
        errors = payload.get("errors") or ["The model request failed."]
        detail = "; ".join(
            str(item.get("message", item)) if isinstance(item, dict) else str(item)
            for item in errors
        )
        raise RuntimeError(f"Cloudflare model error: {detail}")

    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Cloudflare returned no model result.")
    return result


# ---------------------------------------------------------------- IBM Granite chat
CHAT_MODEL = "@cf/ibm-granite/granite-4.0-h-micro"
VISION_MODEL = "@cf/moondream/moondream3.1-9B-A2B"
IMAGE_MODEL = secret("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")


def describe_image(image_b64: str, question: str) -> str:
    """Use Cloudflare Moondream for image input; Granite itself is text-only."""
    if not image_b64:
        return ""

    # Cache per Streamlit session so earlier images in a continuing chat are not
    # analyzed again on every subsequent message.
    cache = st.session_state.setdefault("vision_cache", {})
    cache_key = hashlib.sha256(
        (image_b64 + "\0" + question).encode("utf-8", errors="ignore")
    ).hexdigest()
    if cache_key in cache:
        return cache[cache_key]

    result = cloudflare_run(
        VISION_MODEL,
        {
            "task": "query",
            "image": f"data:image/jpeg;base64,{image_b64}",
            "question": question or "Describe this image.",
            "reasoning": False,
            "stream": False,
            "max_tokens": 1024,
        },
    )
    answer = str(result.get("answer") or result.get("caption") or "").strip()
    if not answer:
        raise RuntimeError("Cloudflare's image model did not return an image description.")

    # Keep this cache bounded for long-running Streamlit sessions.
    if len(cache) >= 32:
        cache.pop(next(iter(cache)))
    cache[cache_key] = answer
    return answer


def granite_chat(messages: list) -> dict:
    """Run chat through IBM Granite, using Moondream only for attached images."""
    clean = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role not in ("system", "user", "assistant"):
            continue

        content = str(message.get("content", "") or "")
        image_descriptions = []
        for index, image_b64 in enumerate(message.get("images") or [], start=1):
            if not isinstance(image_b64, str) or not image_b64:
                continue
            description = describe_image(
                image_b64,
                content.strip() or "Describe this image in useful detail.",
            )
            image_descriptions.append(f"Image {index} analysis: {description}")

        if image_descriptions:
            content = (content + "\n\n" if content else "") + "\n".join(image_descriptions)
        clean.append({"role": role, "content": content})

    if not clean:
        raise RuntimeError("The conversation is empty.")

    if not any(message["role"] == "system" for message in clean):
        clean.insert(
            0,
            {
                "role": "system",
                "content": (
                    "You are a helpful, clear, and accurate assistant. "
                    "Use the supplied image descriptions when the user has attached images. "
                    "Do not claim to see image pixels directly; image descriptions are provided "
                    "by a separate vision model."
                ),
            },
        )

    result = cloudflare_run(
        CHAT_MODEL,
        {
            "messages": clean,
            "max_tokens": 2048,
            "temperature": 0.6,
        },
    )
    text = str(result.get("response") or result.get("text") or "").strip()
    if not text:
        raise RuntimeError("IBM Granite returned an empty response.")

    # Granite 4.0 H Micro returns a normal text response, not a separate
    # user-visible reasoning transcript. Keep the UI's Thinking status, but
    # do not fabricate a thinking field.
    return {"text": text, "thinking": "", "images": []}


def generate_image(prompt: str) -> dict:
    """Generate an image through Cloudflare Workers AI FLUX.1 Schnell."""
    prompt = str(prompt or "").strip()
    if not prompt:
        raise RuntimeError("Enter a description for the image first.")

    if len(prompt) > 2048:
        raise RuntimeError("Image prompts must be 2,048 characters or fewer.")

    result = cloudflare_run(
        IMAGE_MODEL,
        {
            "prompt": prompt,
            "steps": 4,
        },
        timeout=300,
    )
    image_b64 = result.get("image")
    if not isinstance(image_b64, str) or not image_b64:
        raise RuntimeError("Cloudflare's image model did not return image data.")
    return {
        "image": f"data:image/jpeg;base64,{image_b64}",
        "model": IMAGE_MODEL,
    }


# ---------------------------------------------------------------- Streamlit component bridge
st.session_state.setdefault("reply", None)
st.session_state.setdefault("handled", None)
st.session_state.setdefault("vision_cache", {})

value = ascent_ui(reply=st.session_state.reply, key="ascent", default=None)

if isinstance(value, dict) and value.get("id") and value["id"] != st.session_state.handled:
    st.session_state.handled = value["id"]
    try:
        if value.get("mode") == "image":
            result = generate_image(value.get("prompt", ""))
        else:
            result = granite_chat(value.get("messages") or [])
        st.session_state.reply = {"id": value["id"], **result}
    except Exception as exc:  # shown inside the Ascent interface as an error bubble
        st.session_state.reply = {"id": value["id"], "error": str(exc)}
    st.rerun()

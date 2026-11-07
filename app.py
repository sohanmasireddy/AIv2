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


# ---------------------------------------------------------------- Gemma 4 chat + image models
CHAT_MODEL = "@cf/google/gemma-4-26b-a4b-it"
VISION_MODEL = "@cf/moondream/moondream3.1-9B-A2B"
IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"


def describe_image(image_b64: str, question: str) -> str:
    """Use Moondream for image uploads and pass its description to Gemma 4."""
    if not image_b64:
        return ""

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
        raise RuntimeError("Cloudflare's image-understanding model returned no description.")

    if len(cache) >= 32:
        cache.pop(next(iter(cache)))
    cache[cache_key] = answer
    return answer


def _content_to_text(content) -> str:
    """Normalize OpenAI-compatible message content into displayable text."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    return str(content or "").strip()


def gemma_chat(messages: list) -> dict:
    """Run chat through Cloudflare's OpenAI-compatible Gemma 4 endpoint."""
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
                    "Use the supplied image descriptions when the user attaches images. "
                    "Do not claim to see image pixels directly; image descriptions are "
                    "provided by a separate vision model."
                ),
            },
        )

    account_id, api_token = cloudflare_credentials()
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/v1/chat/completions"
    )
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": CHAT_MODEL,
                "messages": clean,
                "max_completion_tokens": 2048,
                "temperature": 0.6,
                "stream": False,
            },
            timeout=300,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach Cloudflare Gemma 4: {exc}") from exc

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(
            f"Cloudflare returned a non-JSON response (HTTP {response.status_code}): "
            f"{response.text[:600]}"
        ) from None

    if not response.ok:
        detail = payload.get("error", payload.get("errors", payload))
        raise RuntimeError(f"Cloudflare Gemma 4 returned HTTP {response.status_code}: {detail}")

    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(
            "Gemma 4 returned no choices. Cloudflare response keys: "
            + ", ".join(str(key) for key in payload.keys())
        )

    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message") or {}
    answer = _content_to_text(message.get("content"))
    if not answer:
        reason = choice.get("finish_reason") or "not provided"
        raise RuntimeError(f"Gemma 4 returned an empty message (finish reason: {reason}).")

    thinking = _content_to_text(
        message.get("reasoning") or message.get("reasoning_content") or ""
    )
    return {"text": answer, "thinking": thinking, "images": []}


def generate_image(prompt: str) -> dict:
    """Generate an image through Cloudflare FLUX.2 Klein 4B (multipart REST API)."""
    prompt = str(prompt or "").strip()
    if not prompt:
        raise RuntimeError("Enter a description for the image first.")
    if len(prompt) > 2048:
        raise RuntimeError("Image prompts must be 2,048 characters or fewer.")

    account_id, api_token = cloudflare_credentials()
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/{IMAGE_MODEL}"
    )
    # FLUX.2 Klein 4B requires multipart/form-data, even for text-only generation.
    # Four inference steps are fixed by Cloudflare for this distilled model.
    multipart_fields = {
        "prompt": (None, prompt),
        "width": (None, "1024"),
        "height": (None, "768"),
    }
    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_token}"},
            files=multipart_fields,
            timeout=300,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach Cloudflare FLUX.2 Klein: {exc}") from exc

    if not response.ok:
        detail = response.text[:1000]
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("errors") or payload.get("error") or detail
        except ValueError:
            pass
        raise RuntimeError(f"FLUX.2 Klein returned HTTP {response.status_code}: {detail}")

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    image_bytes = response.content
    image_b64 = None

    # Cloudflare may return the generated image as raw bytes or a JSON result.
    if content_type == "application/json" or content_type.endswith("+json"):
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if isinstance(payload, dict) and payload.get("success") is False:
            detail = payload.get("errors") or payload.get("error") or payload
            raise RuntimeError(f"FLUX.2 Klein model error: {detail}")
        result = payload.get("result", payload) if isinstance(payload, dict) else {}
        if isinstance(result, dict):
            image_b64 = result.get("image") or result.get("data") or payload.get("image")
            content_type = result.get("mime_type") or result.get("content_type") or "image/png"
        elif isinstance(result, str):
            image_b64 = result
        if not isinstance(image_b64, str) or not image_b64:
            raise RuntimeError("FLUX.2 Klein returned JSON without an image field.")
        if image_b64.startswith("data:") and "," in image_b64:
            data_uri_header, image_b64 = image_b64.split(",", 1)
            if ";base64" in data_uri_header:
                content_type = data_uri_header[5:].split(";", 1)[0]
        import base64
        try:
            image_bytes = base64.b64decode(image_b64, validate=True)
        except Exception as exc:
            raise RuntimeError("FLUX.2 Klein returned invalid base64 image data.") from exc

    if not image_bytes:
        raise RuntimeError("FLUX.2 Klein returned an empty image.")

    # Detect a usable image MIME type if the server labels the binary generically.
    if content_type not in ("image/png", "image/jpeg", "image/webp"):
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            content_type = "image/png"
        elif image_bytes.startswith(b"\xff\xd8\xff"):
            content_type = "image/jpeg"
        elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            content_type = "image/webp"
        else:
            content_type = "image/png"

    import base64
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return {
        "image": f"data:{content_type};base64,{encoded}",
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
            result = gemma_chat(value.get("messages") or [])
        st.session_state.reply = {"id": value["id"], **result}
    except Exception as exc:  # shown inside the Ascent interface as an error bubble
        st.session_state.reply = {"id": value["id"], "error": str(exc)}
    st.rerun()

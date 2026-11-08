
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

ascent_ui = components.declare_component(
    "ascent_ui",
    path=str(FRONTEND),
)


# -----------------------------------------------------------------------------
# Cloudflare Workers AI — Google Gemma 4 26B A4B
# -----------------------------------------------------------------------------
MODEL = "@cf/google/gemma-4-26b-a4b-it"

DEFAULT_CLOUDFLARE_ENDPOINT = (
    "https://api.cloudflare.com/client/v4"
)

SYSTEM_PROMPT = (
    "You are a helpful, clear, and accurate AI assistant. "
    "When the user attaches an image, inspect it and answer questions "
    "about its contents. If something in an image is unclear, "
    "say so instead of guessing."
)


def secret(name: str, default: str = "") -> str:
    """Read Streamlit Secrets first, then environment variables."""
    try:
        value = st.secrets[name]
    except Exception:
        value = None

    return str(value or os.environ.get(name, default)).strip()


def cloudflare_credentials() -> tuple[str, str]:
    account_id = secret("CLOUDFLARE_ACCOUNT_ID")

    api_token = (
        secret("CLOUDFLARE_API_TOKEN")
        or secret("CLOUDFLARE_AUTH_TOKEN")
    )

    if not account_id or not api_token:
        raise RuntimeError(
            "Cloudflare is not configured. Add CLOUDFLARE_ACCOUNT_ID "
            "and CLOUDFLARE_API_TOKEN to Streamlit Secrets."
        )

    return account_id, api_token


def _cloudflare_error_detail(
    payload: Any,
    fallback: str
) -> str:
    """Extract Cloudflare error messages without exposing credentials."""
    if isinstance(payload, dict):
        errors = payload.get("errors")

        if isinstance(errors, list) and errors:
            parts = []

            for item in errors:
                if isinstance(item, dict):
                    code = item.get("code")
                    message = item.get("message") or str(item)

                    parts.append(
                        f"{code}: {message}"
                        if code is not None
                        else str(message)
                    )
                else:
                    parts.append(str(item))

            return "; ".join(parts)

        error = payload.get("error")

        if isinstance(error, dict):
            return str(error.get("message") or error)

        if error:
            return str(error)

        if payload.get("message"):
            return str(payload["message"])

    return fallback


def explain_cloudflare_error(
    status_code: int,
    detail: str
) -> str:
    """Explain common Cloudflare errors."""
    lower = detail.lower()

    if status_code in (401, 403):
        return (
            "Cloudflare rejected the API token or denied Workers AI access. "
            "Check that the token belongs to this account and has Account → "
            "Workers AI → Read permission. Details: " + detail
        )

    if status_code == 429:
        if any(
            term in lower
            for term in ("capacity", "3040", "busy", "queue")
        ):
            return (
                "Cloudflare Workers AI is temporarily at capacity. "
                "Try again later. Details: " + detail
            )

        return (
            "Cloudflare rate-limited this request or a usage limit was reached. "
            "The Workers Free allowance is shared across models and resets "
            "daily at 00:00 UTC. Check Workers AI usage in your Cloudflare "
            "dashboard. Details: " + detail
        )

    if status_code == 400 and any(
        term in lower for term in ("image", "content", "vision")
    ):
        return (
            "Cloudflare did not accept the image-message format. "
            "The text-only request may still work; check the model's "
            "current vision input requirements. Details: " + detail
        )

    return (
        f"Cloudflare Workers AI returned HTTP {status_code}: {detail}"
    )


def _message_for_cloudflare(message: dict) -> dict | None:
    """Normalize frontend history into Cloudflare's multimodal format."""
    role = message.get("role")

    if role not in ("system", "user", "assistant"):
        return None

    text = str(message.get("content", "") or "")
    images = message.get("images") or []

    if role != "user" or not images:
        return {
            "role": role,
            "content": text
        }

    # Cloudflare Workers AI vision content format.
    parts: list[dict] = []

    if text:
        parts.append({
            "type": "text",
            "text": text
        })
    else:
        parts.append({
            "type": "text",
            "text": "Describe this image."
        })

    for image in images:
        if not isinstance(image, str) or not image.strip():
            continue

        image_value = image.strip()

        if not image_value.startswith("data:"):
            image_value = "data:image/jpeg;base64," + image_value

        parts.append({
            "type": "image",
            "image": image_value
        })

    return {
        "role": role,
        "content": parts
    }


def gemma_chat(messages: list[dict]) -> str:
    """Send chat history, including uploaded images, to Cloudflare Gemma 4."""
    account_id, api_token = cloudflare_credentials()

    clean_messages = []

    for item in messages:
        if not isinstance(item, dict):
            continue

        normalized = _message_for_cloudflare(item)

        if normalized is not None:
            clean_messages.append(normalized)

    if not clean_messages:
        raise RuntimeError("The conversation is empty.")

    if not any(
        message["role"] == "system"
        for message in clean_messages
    ):
        clean_messages.insert(
            0,
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        )

    endpoint = (
        f"{DEFAULT_CLOUDFLARE_ENDPOINT}/accounts/"
        f"{account_id}/ai/run/{MODEL}"
    )

    request_body = {
        "messages": clean_messages,
        "stream": False,
        "temperature": 0.6,
        "chat_template_kwargs": {
            "enable_thinking": False
        },
    }

    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json=request_body,
            timeout=(15, 300),
        )

    except requests.Timeout as exc:
        raise RuntimeError(
            "Cloudflare took too long to respond. Please retry."
        ) from exc

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not connect to Cloudflare Workers AI: {exc}"
        ) from exc

    try:
        payload = response.json()

    except ValueError:
        raise RuntimeError(
            f"Cloudflare returned a non-JSON response "
            f"(HTTP {response.status_code}): "
            f"{response.text[:800]}"
        ) from None

    if not response.ok:
        detail = _cloudflare_error_detail(
            payload,
            response.text[:1000]
        )

        raise RuntimeError(
            explain_cloudflare_error(
                response.status_code,
                detail
            )
        )

    if (
        isinstance(payload, dict)
        and payload.get("success") is False
    ):
        detail = _cloudflare_error_detail(
            payload,
            "The model request failed."
        )

        raise RuntimeError(
            "Cloudflare model error: " + detail
        )

    # Workers AI /ai/run normally wraps model output in {result: ...}.
    # Also tolerate an unwrapped result or OpenAI-style response.
    result = (
        payload.get("result", payload)
        if isinstance(payload, dict)
        else payload
    )

    answer = ""

    if isinstance(result, dict):
        answer = (
            result.get("response")
            or result.get("text")
            or ""
        )

        if (
            not answer
            and isinstance(result.get("choices"), list)
            and result["choices"]
        ):
            first = result["choices"][0] or {}
            message = first.get("message") or {}
            answer = message.get("content") or ""

    elif isinstance(result, str):
        answer = result

    if isinstance(answer, list):
        answer = "\n".join(
            part.get("text", "")
            for part in answer
            if (
                isinstance(part, dict)
                and isinstance(part.get("text"), str)
            )
        )

    answer = str(answer or "").strip()

    if not answer:
        keys = (
            list(result.keys())
            if isinstance(result, dict)
            else [type(result).__name__]
        )

        raise RuntimeError(
            "Gemma 4 returned no visible text. Response fields: "
            + ", ".join(str(key) for key in keys)
        )

    return answer


# -----------------------------------------------------------------------------
# Streamlit component request handling
# -----------------------------------------------------------------------------
st.session_state.setdefault("reply", None)
st.session_state.setdefault("handled", None)

value = ascent_ui(
    reply=st.session_state.reply,
    key="ascent",
    default=None
)

if (
    isinstance(value, dict)
    and value.get("id")
    and value["id"] != st.session_state.handled
):
    st.session_state.handled = value["id"]

    try:
        answer = gemma_chat(
            value.get("messages") or []
        )

        st.session_state.reply = {
            "id": value["id"],
            "text": answer
        }

    except Exception as exc:
        st.session_state.reply = {
            "id": value["id"],
            "error": str(exc)
        }

    st.rerun()

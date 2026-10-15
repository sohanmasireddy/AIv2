import hmac
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Liquid Glass AI", page_icon="💧", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""<style>
#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],[data-testid="stAppDeployButton"],.stDeployButton{display:none!important}
html,body,.stApp{background:#0b0708!important}
.block-container{padding:0!important;max-width:none!important}
iframe[src*="liquid_glass_chat"]{position:fixed!important;inset:0!important;width:100vw!important;
height:100dvh!important;border:0!important;z-index:999}
</style>""", unsafe_allow_html=True)

PROVIDERS = {
    "ollama": {"label": "Ollama Cloud", "endpoint": "https://ollama.com", "model": "gpt-oss:120b"},
    "openai": {"label": "OpenAI-compatible", "endpoint": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
}
_ui = components.declare_component("liquid_glass_chat", path=str(Path(__file__).parent / "frontend"))


def secret(section):
    try:
        return dict(st.secrets.get(section, {}))
    except Exception:
        return {}


def prov(name):
    d, s = dict(PROVIDERS[name]), secret(name)
    d["endpoint"] = s.get("endpoint", d["endpoint"]).rstrip("/")
    d["model"] = s.get("model", d["model"])
    d["has_key"] = bool(s.get("api_key"))
    return d


def ask(cfg, history):
    name = cfg.get("provider")
    if name not in PROVIDERS:
        raise ValueError("Unknown provider")
    d = prov(name)
    endpoint = (cfg.get("endpoint") or d["endpoint"]).strip().rstrip("/")
    u = urlparse(endpoint)
    if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1"))):
        raise ValueError("Endpoint must use https://")
    key = (cfg.get("api_key") or "").strip()
    # Never send the server secret to an endpoint the visitor changed.
    if not key and endpoint == d["endpoint"]:
        key = secret(name).get("api_key", "")
    model = str(cfg.get("model") or d["model"])[:200]
    temp = min(max(float(cfg.get("temperature", 0.7)), 0.0), 2.0)
    top_p = min(max(float(cfg.get("top_p", 1.0)), 0.0), 1.0)
    max_tokens = min(max(int(cfg.get("max_tokens", 1024)), 1), 32768)
    system = str(cfg.get("system") or "").strip()
    msgs = ([{"role": "system", "content": system}] if system else []) + history
    headers = {"Authorization": f"Bearer {key}"} if key else {}

    if name == "ollama":
        url = f"{endpoint}/api/chat"
        body = {"model": model, "messages": msgs, "stream": False,
                "options": {"temperature": temp, "top_p": top_p, "num_predict": max_tokens}}
    else:
        url = f"{endpoint}/chat/completions"
        body = {"model": model, "messages": msgs, "temperature": temp,
                "top_p": top_p, "max_tokens": max_tokens}
    r = requests.post(url, headers=headers, json=body, timeout=120)
    if not r.ok:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    j = r.json()
    return j["message"]["content"] if name == "ollama" else j["choices"][0]["message"]["content"]


# Optional access code so strangers can't spend your API credits
code = secret("app").get("access_code")
if code and not st.session_state.get("ok"):
    entered = st.text_input("Access code", type="password")
    if entered and hmac.compare_digest(entered.encode(), str(code).encode()):
        st.session_state.ok = True
        st.rerun()
    st.stop()

st.session_state.setdefault("msgs", [])
st.session_state.setdefault("seen", None)

val = _ui(messages=st.session_state.msgs,
          providers={k: prov(k) for k in PROVIDERS},
          reply_to=st.session_state.seen,
          bg=secret("ui").get("background_url"),
          key="ui", default=None)

if val and val.get("id") != st.session_state.seen:
    st.session_state.seen = val["id"]
    if val.get("type") == "clear":
        st.session_state.msgs = []
    else:
        st.session_state.msgs.append({"role": "user", "content": str(val.get("text", ""))[:20000]})
        history = [{"role": m["role"], "content": m["content"]}
                   for m in st.session_state.msgs if not m.get("error")]
        try:
            out = {"role": "assistant", "content": ask(val.get("settings", {}), history)}
        except Exception as e:
            out = {"role": "assistant", "content": f"⚠️ {e}", "error": True}
        st.session_state.msgs.append(out)
    st.rerun()

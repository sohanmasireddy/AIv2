import hashlib
import hmac
import tempfile
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

UI_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Liquid Glass AI</title>
<style>
:root{--text:#fff3e4}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:#0b0708;color:var(--text);-webkit-font-smoothing:antialiased;line-height:1.5;height:100svh;overflow:hidden;position:relative}
@media(max-width:768px){.lil-gui{display:none!important}}
.bg{position:absolute;inset:0;overflow:hidden;z-index:0}
.bg img{width:100%;height:100%;object-fit:cover;display:block;user-select:none;-webkit-user-drag:none}
.global-nav{position:fixed;top:1rem;left:1rem;z-index:10000;width:290px;max-width:calc(100vw - 2rem)}
.nav-container{background:#120d0e;backdrop-filter:blur(16px);border-radius:12px;border:.5px solid #1e1e20;overflow:hidden;box-shadow:0 4px 16px rgb(0 0 0/20%)}
.nav-toggle{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:transparent;border:none;color:#f0f0f0;cursor:pointer;font-size:14px;font-weight:500;width:100%;text-align:left}
.nav-toggle:hover{background:rgb(21 21 25)}
.nav-toggle svg{width:16px;height:16px;fill:currentColor;transition:transform .3s cubic-bezier(.4,0,.2,1)}
.nav-container.expanded .nav-toggle svg{transform:rotate(180deg)}
.nav-menu{max-height:0;overflow:hidden;transition:max-height .3s cubic-bezier(.4,0,.2,1)}
.nav-container.expanded .nav-menu{max-height:min(70svh,600px);overflow-y:auto}
.field{display:block;padding:10px 16px;border-top:.5px solid #1e1e20;font-size:12px;color:#88888f}
.field b{float:right;font-weight:400;color:#f0f0f0}
.field input,.field select,.field textarea{display:block;width:100%;margin-top:6px;padding:7px 9px;background:rgb(39 39 42/50%);border:0;border-radius:4px;color:#f0f0f0;font-size:13px;font-family:inherit;outline:none}
.field input[type=range]{padding:0;height:18px;accent-color:#ffb45e}
.field input[type=file]{padding:5px}
.field textarea{resize:vertical;min-height:60px}
.hint{padding:8px 16px;border-top:.5px solid #1e1e20;font-size:11px;color:#88888f}
.stage{position:fixed;inset:0;display:flex;justify-content:center;align-items:center;pointer-events:none;z-index:100;padding:1rem}
.glass>*{position:relative;z-index:2}
.chat-card{position:relative;width:min(780px,94vw);height:min(660px,82svh);border-radius:30px;display:flex;flex-direction:column;gap:14px;padding:22px;color:var(--text);pointer-events:auto!important}
.chat-card.fallback{background:rgba(24,14,10,.35);backdrop-filter:blur(24px) saturate(1.4);box-shadow:inset 0 0 0 1px rgba(255,240,225,.16),0 20px 60px rgba(0,0,0,.35)}
.deck-eyebrow{display:flex;align-items:center;justify-content:space-between;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:rgba(255,240,225,.9)}
.eyebrow-live{display:flex;align-items:center;letter-spacing:-.02em;gap:8px}
.live-dot{width:6px;height:6px;border-radius:50%;background:#ffd7b3;box-shadow:0 0 8px rgba(255,161,74,.9);animation:pulse 2.2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.eyebrow-right{display:flex;align-items:center;gap:12px}
.deck-rpm{font-family:"SFMono-Regular",Menlo,Consolas,monospace;font-weight:400;letter-spacing:.08em;color:rgba(255,235,215,.7);max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.player-btn{background:none;border:none;color:rgba(255,235,215,.85);cursor:pointer;display:flex;align-items:center;justify-content:center;transition:color .2s,transform .15s}
.player-btn:hover{color:#fff}.player-btn:active{transform:scale(.92)}
.player-btn:disabled{opacity:.4;cursor:default}
.player-btn svg{width:18px;height:18px;fill:currentColor}
.player-btn-play{width:42px;height:42px;flex-shrink:0;border-radius:50%;border:1px solid rgba(255,200,140,.55);background:rgba(255,170,90,.08);color:#ffd9ae}
.log{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:12px;padding-right:6px;scrollbar-width:thin;scrollbar-color:rgba(255,235,215,.3) transparent}
.msg{max-width:88%;font-size:14.5px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere;text-shadow:0 1px 8px rgba(0,0,0,.35)}
.msg.user{align-self:flex-end;padding:9px 14px;border-radius:18px;background:rgba(255,170,90,.14);box-shadow:inset 0 0 0 1px rgba(255,200,140,.25)}
.msg.assistant{align-self:flex-start;color:#ffedd6}
.msg.error{color:#ffb4a2}
.msg code{font-family:"SFMono-Regular",Menlo,Consolas,monospace;font-size:12.5px;background:rgba(0,0,0,.3);padding:1px 5px;border-radius:5px}
.msg pre{background:rgba(0,0,0,.38);padding:10px 12px;border-radius:12px;margin:6px 0;overflow-x:auto}
.msg pre code{background:none;padding:0}
.empty{margin:auto;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:rgba(255,214,163,.7)}
.control-bar{display:flex;align-items:flex-end;gap:12px;padding-top:6px}
.control-bar textarea{flex:1;resize:none;max-height:120px;background:rgba(255,240,225,.08);border:1px solid rgba(255,200,140,.28);border-radius:21px;padding:11px 16px;color:var(--text);font-family:inherit;font-size:14px;line-height:1.4;outline:none}
.control-bar textarea::placeholder{color:rgba(255,235,215,.5)}
.demo-disclaimer{position:fixed;bottom:1.2rem;left:50%;transform:translateX(-50%);width:100%;max-width:460px;padding:0 1rem;text-align:center;text-transform:uppercase;z-index:10001;pointer-events:none;color:rgba(255,255,255,.92)}
.disclaimer-feature{font-size:12px;font-weight:800;letter-spacing:.02em;margin-bottom:4px}
.disclaimer-note{font-size:9px;letter-spacing:-.02em;color:rgba(255,255,255,.6)}
@media(max-width:640px){.disclaimer-note{display:none}}
</style>
</head>
<body>
<div class="bg"><img id="bgimg" alt="" /></div>

<nav class="global-nav">
  <div class="nav-container" id="nav">
    <button class="nav-toggle" id="navBtn" aria-expanded="false"><span>Settings</span><svg viewBox="0 0 16 16"><path d="M8 11L3 6h10l-5 5z"/></svg></button>
    <div class="nav-menu">
      <label class="field">Provider<select data-k="provider" id="provider"><option value="ollama">Ollama Cloud</option><option value="openai">OpenAI-compatible</option></select></label>
      <label class="field">Model<input data-k="model" id="model" autocomplete="off" /></label>
      <label class="field">Endpoint<input data-k="endpoint" id="endpoint" autocomplete="off" /></label>
      <label class="field">API key<input data-k="api_key" id="api_key" type="password" autocomplete="new-password" /></label>
      <label class="field">Temperature <b id="v_temperature"></b><input data-k="temperature" id="temperature" type="range" min="0" max="2" step="0.05" /></label>
      <label class="field">Top-p <b id="v_top_p"></b><input data-k="top_p" id="top_p" type="range" min="0" max="1" step="0.05" /></label>
      <label class="field">Max tokens<input data-k="max_tokens" id="max_tokens" type="number" min="1" max="32768" step="64" /></label>
      <label class="field">System prompt<textarea data-k="system" id="system"></textarea></label>
      <label class="field">Background<select id="bgPreset"><option value="0">Aurora</option><option value="1">Sunset</option><option value="2">Ocean</option><option value="3">Mono</option></select></label>
      <label class="field">Upload image (stays in your browser)<input id="bgFile" type="file" accept="image/*" /></label>
      <label class="field">Image URL (needs CORS)<input id="bgUrl" placeholder="https://…" autocomplete="off" /></label>
      <label class="field">Renderer<select id="engine"><option value="webgpu">WebGPU (client-side)</option><option value="auto">Auto (WebGPU → WebGL)</option><option value="webgl2">WebGL2</option></select></label>
      <div class="hint" id="gpu"></div>
    </div>
  </div>
</nav>

<div class="stage">
  <div class="chat-card glass" id="card">
    <div class="deck-eyebrow">
      <span class="eyebrow-live"><span class="live-dot"></span><span id="status">Live</span></span>
      <span class="eyebrow-right"><span class="deck-rpm" id="modelTag"></span>
        <button class="player-btn" id="clear" aria-label="Clear chat"><svg viewBox="0 0 24 24"><path d="M6 7h12l-1 13H7zM9 4h6l1 2H8z"/></svg></button></span>
    </div>
    <div class="log" id="log"></div>
    <form class="control-bar" id="form">
      <textarea id="inp" rows="1" placeholder="Message…"></textarea>
      <button class="player-btn player-btn-play" id="send" type="submit" aria-label="Send"><svg viewBox="0 0 24 24" style="width:20px;height:20px"><path d="M12 4l7 7-1.4 1.4L13 7.8V20h-2V7.8l-4.6 4.6L5 11z"/></svg></button>
    </form>
  </div>
</div>

<div class="demo-disclaimer"><p class="disclaimer-feature" id="foot"></p><p class="disclaimer-note">Liquid glass by liquidGL · rendered in your browser</p></div>

<script>
const BASE = "https://cdn.jsdelivr.net/gh/naughtyduk/liquidGL@main/scripts/";
const $ = id => document.getElementById(id);
const send = (type, d = {}) => parent.postMessage({ isStreamlitMessage: true, type: "streamlit:" + type, ...d }, "*");
const PK = ["model", "endpoint", "api_key"];
let A = {}, P = {}, msgs = [], pending = null, booted = false, lens = null, libReady = null;
const S = { provider: "ollama", temperature: 0.7, top_p: 1, max_tokens: 1024, system: "You are a helpful assistant.", p: {} };

/* ---------- text overlay (plain HTML, escaped) ---------- */
const esc = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const md = t => esc(String(t))
  .replace(/```(?:\w+)?\n?([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
  .replace(/`([^`\n]+)`/g, "<code>$1</code>")
  .replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>");

function render() {
  const list = pending ? [...msgs, { role: "assistant", content: "…" }] : msgs;
  $("log").innerHTML = list.length
    ? list.map(m => `<div class="msg ${m.role}${m.error ? " error" : ""}">${md(m.content)}</div>`).join("")
    : '<div class="empty">Ask anything</div>';
  $("log").scrollTop = $("log").scrollHeight;
  $("send").disabled = !!pending;
  $("status").textContent = pending ? "Thinking" : "Live";
}

/* ---------- settings ---------- */
function fillForm() {
  const d = P[S.provider] || {}, o = S.p[S.provider] || {};
  $("provider").value = S.provider;
  PK.forEach(k => $(k).value = o[k] ?? (k === "api_key" ? "" : d[k] ?? ""));
  ["temperature", "top_p", "max_tokens", "system"].forEach(k => { $(k).value = S[k]; if ($("v_" + k)) $("v_" + k).textContent = S[k]; });
  $("api_key").placeholder = d.has_key ? "Optional — server secret in use" : "Required";
  head();
}
function head() {
  const d = P[S.provider] || {};
  $("modelTag").textContent = $("model").value;
  $("foot").textContent = (d.label || "") + " · " + $("model").value;
}
document.querySelectorAll("[data-k]").forEach(el => el.addEventListener("input", () => {
  const k = el.dataset.k;
  if (k === "provider") { S.provider = el.value; fillForm(); return; }
  if (PK.includes(k)) (S.p[S.provider] ??= {})[k] = el.value;
  else S[k] = el.tagName === "TEXTAREA" ? el.value : +el.value;
  if ($("v_" + k)) $("v_" + k).textContent = S[k];
  head();
}));
const settings = () => {
  const o = S.p[S.provider] || {}, d = P[S.provider] || {};
  return { provider: S.provider, model: o.model || d.model, endpoint: o.endpoint || d.endpoint, api_key: o.api_key || "",
           temperature: S.temperature, top_p: S.top_p, max_tokens: S.max_tokens, system: S.system };
};

/* ---------- chat ---------- */
const inp = $("inp");
inp.addEventListener("input", () => { inp.style.height = "auto"; inp.style.height = Math.min(inp.scrollHeight, 120) + "px"; });
inp.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("form").requestSubmit(); } });
$("form").addEventListener("submit", e => {
  e.preventDefault();
  const text = inp.value.trim();
  if (!text || pending) return;
  const id = pending = crypto.randomUUID();
  msgs = [...msgs, { role: "user", content: text }];
  inp.value = ""; inp.style.height = "auto";
  render();
  send("setComponentValue", { value: { id, type: "send", text, settings: settings() }, dataType: "json" });
  setTimeout(() => { if (pending === id) { pending = null; render(); } }, 150000);
});
$("clear").addEventListener("click", () => {
  pending = null; msgs = []; render();
  send("setComponentValue", { value: { id: crypto.randomUUID(), type: "clear" }, dataType: "json" });
});
$("navBtn").addEventListener("click", () => { const x = $("nav").classList.toggle("expanded"); $("navBtn").setAttribute("aria-expanded", x); });
document.addEventListener("click", e => { if (!$("nav").contains(e.target)) $("nav").classList.remove("expanded"); });
document.addEventListener("keydown", e => { if (e.key === "Escape") $("nav").classList.remove("expanded"); });

/* ---------- background ---------- */
const PALETTES = [
  ["#1b0f2e", "#3a1646", "#0d2b3a", "#ff7a3d", "#6a5cff", "#ff3d8b", "#2ad4c0"],
  ["#2b0f0f", "#5a1f2a", "#2a1646", "#ffb02e", "#ff5d5d", "#ff3d8b", "#8a5cff"],
  ["#04121f", "#0a2a4a", "#062f3a", "#1ec8ff", "#2a6cff", "#2ad4a0", "#7a5cff"],
  ["#0b0b0d", "#1c1c20", "#0f0f12", "#d8d8e0", "#8a8a96", "#f0f0f5", "#5a5a66"],
];
function presetURL(i) {
  const c = PALETTES[i] || PALETTES[0];
  const L = (n, f) => Array.from({ length: n }, (_, k) => f(k)).join("");
  const grid = L(21, k => `M${k * 80} 0V1000M0 ${k * 50}H1600`);
  const rings = L(8, k => `<circle cx="800" cy="500" r="${60 + k * 70}"/>`);
  const s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${c[0]}"/><stop offset=".55" stop-color="${c[1]}"/><stop offset="1" stop-color="${c[2]}"/></linearGradient><filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="70"/></filter></defs><rect width="1600" height="1000" fill="url(#g)"/><g filter="url(#b)"><circle cx="300" cy="260" r="260" fill="${c[3]}"/><circle cx="1250" cy="200" r="230" fill="${c[4]}"/><circle cx="880" cy="800" r="300" fill="${c[5]}"/><circle cx="1420" cy="780" r="190" fill="${c[6]}"/></g><g stroke="#fff" stroke-opacity=".3" stroke-width="2" fill="none"><path d="${grid}"/>${rings}</g></svg>`;
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(s);
}
async function setBg(src, cors) {
  const img = $("bgimg");
  img.crossOrigin = cors ? "anonymous" : null;
  img.src = src;
  try { await img.decode(); } catch (e) { alert("Could not load that image (check the URL / CORS)."); img.src = presetURL(+$("bgPreset").value); await img.decode().catch(() => {}); }
  // re-capture the refraction texture (same call the helper GUI uses)
  const r = window.__liquidGLRenderer__;
  if (r && r.captureSnapshot) r.captureSnapshot();
}
$("bgPreset").addEventListener("change", e => { $("bgUrl").value = ""; $("bgFile").value = ""; setBg(presetURL(+e.target.value)); });
$("bgFile").addEventListener("change", e => {
  const f = e.target.files[0]; if (!f) return;
  const fr = new FileReader(); fr.onload = () => setBg(fr.result); fr.readAsDataURL(f);
});
$("bgUrl").addEventListener("change", e => { const u = e.target.value.trim(); if (u) setBg(u, true); });

/* ---------- liquidGL (runs entirely in the browser) ---------- */
const load = src => new Promise((ok, no) => { const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = no; document.head.appendChild(s); });
function initLens() {
  (window.__liquidGLHelperGUIs__ || []).splice(0).forEach(g => { try { g.gui.destroy(); } catch (e) {} });
  lens = liquidGL({
    engine: $("engine").value, snapshot: ".bg", target: ".glass", resolution: 2,
    content: false,                       // text stays a plain HTML overlay
    refraction: 0.02, aberration: 0.15, bevelDepth: 0.08, bevelWidth: 0.15,
    frost: 2, shadow: true, specular: true, reveal: "fade",
    tilt: false, draggable: false,
    interaction: "fluid", interactionStrength: 0.5, interactionRadius: 0.35, interactionViscosity: 0.65,
    magnify: 1, tint: "rgba(24, 14, 10, 0.25)",
    helper: true
  });
}
$("engine").addEventListener("change", () => {
  try { if (lens && lens.destroy) lens.destroy(); initLens(); } catch (e) { console.warn(e); $("card").classList.add("fallback"); }
});
async function initGlass() {
  $("gpu").textContent = navigator.gpu ? "WebGPU is available in this browser." : "WebGPU not available here — choose Auto or WebGL2.";
  await setBg(A.bg || presetURL(0), !!A.bg);
  try {
    await Promise.all([load(BASE + "liquidGL.js"), load(BASE + "liquidGL-helper.js")]);
    initLens();
  } catch (e) {
    console.warn("liquidGL failed to load, using CSS fallback", e);
    $("card").classList.add("fallback");
  }
}

/* ---------- Streamlit component protocol ---------- */
addEventListener("message", e => {
  if (e.data?.type !== "streamlit:render") return;
  A = e.data.args || {}; P = A.providers || {};
  if (!pending || A.reply_to === pending) {
    msgs = A.messages || [];
    if (A.reply_to === pending) pending = null;
  }
  if (!booted) { booted = true; fillForm(); initGlass(); }
  render();
});
send("componentReady", { apiVersion: 1 });
send("setFrameHeight", { height: 800 });
</script>
</body>
</html>
'''

# Write the UI next to the OS temp dir so no extra repo folder is required.
_dir = Path(tempfile.gettempdir()) / ("lg_chat_" + hashlib.md5(UI_HTML.encode()).hexdigest()[:10])
_dir.mkdir(parents=True, exist_ok=True)
(_dir / "index.html").write_text(UI_HTML, encoding="utf-8")
_ui = components.declare_component("liquid_glass_chat", path=str(_dir))

PROVIDERS = {
    "ollama": {"label": "Ollama Cloud", "endpoint": "https://ollama.com", "model": "gpt-oss:120b"},
    "openai": {"label": "OpenAI-compatible", "endpoint": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
}


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

import hashlib
import hmac
import shutil
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
[data-testid="stStatusWidget"],[data-testid="stAppDeployButton"],.stDeployButton,
[class*="viewerBadge"],[class*="profileContainer"],[class*="profilePreview"],
a[href*="streamlit.io"]{display:none!important}
html,body,.stApp{background:#10151d!important}
.block-container{padding:0!important;max-width:none!important}
iframe[src*="liquid_glass_chat"]{position:fixed!important;inset:0!important;width:100vw!important;
height:100dvh!important;border:0!important;z-index:999}
</style>""", unsafe_allow_html=True)

UI_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Liquid Glass AI</title>
<style>
:root{color-scheme:dark;--text:#f7f9fc;--muted:rgba(247,249,252,.67);--glass-border:rgba(255,255,255,.28);--glass-fill:rgba(231,241,255,.065)}
*{box-sizing:border-box}
html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#10151d;color:var(--text);font:500 15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
button,textarea,input,select{font:inherit;color:inherit}
#scene{position:fixed;inset:0;z-index:0;overflow:hidden;background:#17222e}
#scene img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;user-select:none;-webkit-user-drag:none}
.scene-shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(8,15,25,.12) 0%,rgba(8,15,25,.23) 44%,rgba(6,11,18,.58) 100%),linear-gradient(90deg,rgba(7,16,26,.18),transparent 65%);pointer-events:none}
#app{position:fixed;inset:0;z-index:1;display:flex;flex-direction:column;min-width:0;min-height:0}
main{position:relative;flex:1;min-height:0;display:flex;flex-direction:column}
#msgs{flex:1;min-height:0;overflow:auto;display:flex;flex-direction:column;gap:15px;padding:76px clamp(16px,calc((100vw - 920px)/2),30vw) 22px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.24) transparent;overscroll-behavior:contain}
#msgs::-webkit-scrollbar{width:7px}
#msgs::-webkit-scrollbar-thumb{background:rgba(255,255,255,.22);border-radius:99px}
.message-row{display:flex;width:100%;flex:none;min-width:0}
.message-row.user{justify-content:flex-end}
.message-row.assistant{justify-content:flex-start}
.message-shell{position:relative;width:fit-content;max-width:min(820px,100%);min-width:0;padding:12px 17px;border-radius:22px;overflow:visible;overflow-wrap:anywhere}
.message-row.user .message-shell{border-radius:22px 22px 7px 22px}
.message-row.assistant .message-shell{border-radius:22px 22px 22px 7px}
.glass-lens{position:absolute;inset:0;z-index:2;border:1px solid var(--glass-border);border-radius:inherit;background:var(--glass-fill);backdrop-filter:blur(18px) saturate(1.25);-webkit-backdrop-filter:blur(18px) saturate(1.25);pointer-events:none}
.message-content{position:relative;z-index:4;min-width:0;overflow-wrap:anywhere;color:rgba(255,255,255,.96);text-shadow:0 1px 9px rgba(0,0,0,.18)}
.message-content pre{max-width:100%;overflow:auto;margin:10px 0 3px;padding:12px 14px;border-radius:13px;background:rgba(4,9,15,.48);border:1px solid rgba(255,255,255,.11);white-space:pre;overflow-wrap:normal;text-shadow:none}
.message-content code{font:13px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace}
.message-content :not(pre)>code{background:rgba(7,13,21,.45);border:1px solid rgba(255,255,255,.12);padding:1px 5px;border-radius:6px}
.typing{display:inline-flex;gap:5px;align-items:center;height:23px}
.typing i{width:5px;height:5px;border-radius:50%;background:rgba(255,255,255,.82);animation:pulse 1.1s ease-in-out infinite}
.typing i:nth-child(2){animation-delay:.13s}
.typing i:nth-child(3){animation-delay:.26s}
@keyframes pulse{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}
#hello{position:absolute;z-index:5;inset:0 0 86px;display:grid;place-items:center;padding:20px 24px;pointer-events:none;text-align:center}
#hello[hidden]{display:none}
#hello h1{max-width:900px;margin:0;font-size:clamp(32px,5.2vw,68px);line-height:1.03;font-weight:650;letter-spacing:-.055em;color:rgba(255,255,255,.96);background:linear-gradient(110deg,#fff 8%,#f2f7ff 45%,rgba(204,226,255,.9) 75%,#fff 100%);background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent;filter:drop-shadow(0 3px 22px rgba(3,10,20,.24))}
#composer{position:relative;isolation:auto;width:min(900px,calc(100% - 32px));margin:0 auto max(18px,env(safe-area-inset-bottom));padding:9px 10px 9px 20px;border-radius:27px;flex:none}
.composer-inner{position:relative;z-index:4;display:flex;align-items:flex-end;gap:10px;min-width:0}
#ta{display:block;flex:1;min-width:0;max-height:180px;min-height:43px;resize:none;padding:10px 0 9px;margin:0;border:0!important;border-radius:0;background:transparent!important;color:#fff;line-height:1.5;outline:0!important;box-shadow:none!important;appearance:none;-webkit-appearance:none;caret-color:#fff;text-shadow:0 1px 8px rgba(0,0,0,.14)}
#ta:focus,#ta:focus-visible,#ta:active,#composer:focus-within{outline:0!important;box-shadow:none!important;border-color:transparent}
#ta::placeholder{color:rgba(255,255,255,.7)}
.round-shell{position:relative;z-index:2;flex:0 0 44px;width:44px;height:44px;border-radius:50%}
.round-shell .glass-lens{border-radius:50%;background:rgba(245,249,255,.13)}
.round-btn{position:relative;z-index:4;display:grid;place-items:center;width:44px;height:44px;padding:0;border:0;border-radius:50%;background:transparent;color:#fff;font-size:23px;line-height:1;cursor:pointer;transition:transform .16s ease,background .16s ease}
.round-btn:hover{background:rgba(255,255,255,.1)}
.round-btn:active{transform:scale(.94)}
.round-btn:focus-visible{outline:2px solid rgba(255,255,255,.75);outline-offset:3px}
.round-btn:disabled{cursor:default;opacity:.68}
.round-btn svg{width:22px;height:22px;fill:currentColor}
.gear-shell{position:absolute;top:16px;left:16px;z-index:12}

/* model picker (left of send) */
.model-wrap{position:relative;z-index:6;flex:none;align-self:flex-end;margin-bottom:4px}
.model-btn{display:flex;align-items:center;gap:6px;height:36px;max-width:170px;padding:0 12px 0 14px;border-radius:999px;border:1px solid rgba(255,255,255,.2);background:rgba(245,249,255,.1);color:#fff;font-size:13px;cursor:pointer;transition:background .16s ease}
.model-btn:hover{background:rgba(255,255,255,.16)}
.model-btn span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.model-btn svg{width:14px;height:14px;flex:none;fill:currentColor;opacity:.8}
.model-menu{display:none;position:absolute;right:0;bottom:calc(100% + 12px);min-width:200px;padding:6px;border-radius:18px;border:1px solid var(--glass-border);background:rgba(14,20,30,.55);backdrop-filter:blur(26px) saturate(1.4);-webkit-backdrop-filter:blur(26px) saturate(1.4);box-shadow:0 18px 50px rgba(0,0,0,.35)}
.model-menu.open{display:block}
.model-item{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;padding:9px 12px;border:0;border-radius:12px;background:transparent;color:#fff;font-size:13.5px;text-align:left;cursor:pointer}
.model-item:hover{background:rgba(255,255,255,.1)}
.model-item.on::after{content:"✓";opacity:.9}

/* settings menu = liquidGL helper only */
#panel{display:none;position:absolute;z-index:30;top:70px;left:16px;width:320px;max-width:calc(100% - 32px);max-height:calc(100% - 96px);overflow:auto;border-radius:22px;border:1px solid var(--glass-border);background:rgba(14,20,30,.5);backdrop-filter:blur(26px) saturate(1.4);-webkit-backdrop-filter:blur(26px) saturate(1.4);box-shadow:0 18px 50px rgba(0,0,0,.35);scrollbar-width:thin}
#panel.open{display:block}
#panel .lil-gui.root.liquidgl-helper{position:static!important;width:100%!important;max-height:none!important;border:0!important;border-radius:0!important;box-shadow:none!important;backdrop-filter:none!important;background:transparent!important;z-index:auto!important;--background-color:transparent}
#panel .lil-gui.root.liquidgl-helper>.title{display:none}

#status{position:fixed;left:50%;bottom:5px;transform:translateX(-50%);width:max-content;max-width:calc(100% - 32px);font-size:12px;color:rgba(255,255,255,.9);text-align:center;text-shadow:0 1px 8px #000;pointer-events:none}
#status:empty{display:none}
@media(max-width:650px){
#msgs{padding:70px 14px 18px;gap:12px}
.message-shell{padding:11px 14px;max-width:100%}
#composer{width:calc(100% - 20px);margin-bottom:max(12px,env(safe-area-inset-bottom));padding-left:15px;border-radius:23px}
.model-btn{max-width:120px}
#hello{inset:0 0 82px}
#hello h1{font-size:clamp(32px,9vw,49px)}
}
@media(prefers-reduced-motion:reduce){
*,*::before,*::after{animation-duration:.001ms!important;transition-duration:.001ms!important;scroll-behavior:auto!important}
}
</style>
</head>
<body>

<div id="scene" aria-hidden="true">
  <img id="bgimg" src="city.png" alt="">
  <div class="scene-shade"></div>
</div>

<div id="app">
  <div class="round-shell gear-shell">
    <div class="glass-lens" id="gearGlass" aria-hidden="true"></div>
    <button class="round-btn" id="gear" type="button" aria-label="Glass settings" title="Glass settings"><svg viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg></button>
  </div>

  <div id="panel"></div>

  <main>
    <div id="msgs" aria-live="polite" aria-label="Conversation"></div>
    <div id="hello"><h1>What can I help with?</h1></div>
    <div id="composer">
      <div class="glass-lens" id="composerGlass" aria-hidden="true"></div>
      <div class="composer-inner">
        <textarea id="ta" rows="1" placeholder="Ask anything" aria-label="Message" autocomplete="off" spellcheck="true"></textarea>
        <div class="model-wrap" id="modelWrap">
          <button class="model-btn" id="modelBtn" type="button" aria-haspopup="listbox" aria-expanded="false" title="Model"><span id="modelLabel"></span><svg viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg></button>
          <div class="model-menu" id="modelMenu" role="listbox"></div>
        </div>
        <div class="round-shell">
          <div class="glass-lens" id="sendGlass" aria-hidden="true"></div>
          <button class="round-btn" id="send" type="button" aria-label="Send message" title="Send">↑</button>
        </div>
      </div>
    </div>
  </main>
</div>
<div id="status" role="status" aria-live="polite"></div>

<script>
(() => {
  'use strict';
  const BASE = 'https://cdn.jsdelivr.net/gh/naughtyduk/liquidGL@main/scripts/';
  const $ = (s) => document.querySelector(s);
  const post = (type, d = {}) => parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:' + type, ...d }, '*');
  const msgsEl = $('#msgs'), hello = $('#hello'), ta = $('#ta'), sendBtn = $('#send'), statusEl = $('#status'), panel = $('#panel');

  let A = {}, msgs = [], pending = null, booted = false, glassReady = false, counter = 0;
  const rows = [], all = [];
  const S = { model: null };

  /* ---------- hide platform badge (best effort, same-origin frames only) ---------- */
  const BADGE = '[class*="viewerBadge"],[class*="profileContainer"],[class*="profilePreview"],a[href*="streamlit.io"]';
  function frames(w, out = []) { try { out.push(w.document); for (let i = 0; i < w.frames.length; i++) frames(w.frames[i], out); } catch (e) {} return out; }
  function hideBadge() {
    frames(window.top).forEach(d => { try {
      if (!d.getElementById('lg-hide')) { const s = d.createElement('style'); s.id = 'lg-hide'; s.textContent = BADGE + '{display:none!important}'; d.head.appendChild(s); }
    } catch (e) {} });
  }
  hideBadge(); setInterval(hideBadge, 2000);

  /* ---------- liquid glass ---------- */
  const glassOptions = {
    snapshot: '#scene', engine: navigator.gpu ? 'webgpu' : 'auto', resolution: 3.0, zIndex: 2, content: false,
    refraction: 0.025, bevelDepth: 0.09, bevelWidth: 0.19, frost: 10, aberration: 0.012, magnify: 1,
    shadow: true, specular: true, tint: 'rgba(218,233,255,0.035)', reveal: 'none'
  };
  const INHERIT = ['refraction','aberration','bevelDepth','bevelWidth','magnify','frost','specular','interaction','interactionStrength','interactionRadius','interactionViscosity','tiltFactor','tiltEase'];

  function installLens(el) {
    if (!glassReady || !el) return null;
    try {
      const lens = [].concat(window.liquidGL({ ...glassOptions, target: '#' + el.id }))[0];
      if (!lens) return null;
      const base = all[0];
      if (base && base.options) {            // new bubbles pick up the current helper values
        INHERIT.forEach(k => { if (k in base.options) lens.options[k] = base.options[k]; });
        if (lens.setShadow && 'shadow' in base.options) lens.setShadow(base.options.shadow);
        const t = base.options.tint;
        if (Array.isArray(t) && lens.setTint) lens.setTint('rgba(' + Math.round(t[0]*255) + ',' + Math.round(t[1]*255) + ',' + Math.round(t[2]*255) + ',' + t[3] + ')');
      }
      all.push(lens);
      const g = (window.__liquidGLHelperGUIs__ || [])[0];   // helper controls every lens
      if (g && !g.lenses.includes(lens)) g.lenses.push(lens);
      return lens;
    } catch (err) { console.warn('liquidGL lens failed; CSS glass fallback', err); return null; }
  }
  const load = (src) => new Promise((ok, no) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = no; document.head.appendChild(s); });

  // move the helper's lil-gui into the gear menu
  function adoptGui(tries = 0) {
    const g = (window.__liquidGLHelperGUIs__ || [])[0];
    if (!g) { if (tries < 60) setTimeout(() => adoptGui(tries + 1), 100); return; }
    g.gui.open();
    panel.appendChild(g.gui.domElement);
  }

  async function initGlass() {
    await $('#bgimg').decode().catch(() => {});
    try {
      await Promise.all([load(BASE + 'liquidGL.js'), load(BASE + 'liquidGL-helper.js')]);
      if (typeof window.liquidGL !== 'function') throw new Error('liquidGL did not load');
      glassReady = true;
      const first = ['#composerGlass', '#sendGlass', '#gearGlass'].map(s => installLens($(s))).filter(Boolean);
      if (window.__liquidGLHelper__ && first.length) { window.__liquidGLHelper__(first, { ...glassOptions, target: '#composerGlass' }); adoptGui(); }
      rows.forEach(r => { if (!r.lens) r.lens = installLens(r.lensEl); });
    } catch (e) { console.warn('liquidGL unavailable; CSS glass fallback', e); }
  }

  /* ---------- chat rendering (text is plain HTML over the lenses) ---------- */
  const escapeHTML = (s) => s.replace(/[&<>]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));
  function renderMarkdown(text) {
    return String(text).split(/(```[\s\S]*?```)/g).map(part => {
      if (part.startsWith('```')) {
        const m = part.match(/^```[^\n]*\n?([\s\S]*?)```$/);
        return '<pre><code>' + escapeHTML(m ? m[1] : part.slice(3)) + '</code></pre>';
      }
      return escapeHTML(part).replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
    }).join('');
  }
  const typingMarkup = () => '<span class="typing" aria-label="Generating response"><i></i><i></i><i></i></span>';

  function appendBubble(role) {
    const row = document.createElement('div'); row.className = 'message-row ' + role;
    const shell = document.createElement('div'); shell.className = 'message-shell';
    const lensEl = document.createElement('div'); lensEl.className = 'glass-lens'; lensEl.setAttribute('aria-hidden', 'true'); lensEl.id = 'messageGlass-' + (++counter);
    const content = document.createElement('div'); content.className = 'message-content';
    shell.append(lensEl, content); row.append(shell); msgsEl.append(row);
    return { role, row, content, lensEl, lens: installLens(lensEl), key: null };
  }
  function destroyRow(r) {
    if (!r) return;
    if (r.lens) {
      try { r.lens.destroy && r.lens.destroy(); } catch (e) {}
      const i = all.indexOf(r.lens); if (i > 0) all.splice(i, 1);
      const g = (window.__liquidGLHelperGUIs__ || [])[0];
      if (g) { const j = g.lenses.indexOf(r.lens); if (j > 0) g.lenses.splice(j, 1); }
    }
    r.row.remove();
  }
  function paint(r, m) {
    if (r.role === 'assistant') r.content.innerHTML = m.typing ? typingMarkup() : renderMarkdown(m.content);
    else r.content.textContent = m.content;
  }
  function sync() {
    const list = pending ? [...msgs, { role: 'assistant', content: '', typing: true }] : msgs;
    hello.hidden = list.length > 0;
    rows.splice(list.length).forEach(destroyRow);
    let changed = false;
    list.forEach((m, i) => {
      if (rows[i] && rows[i].role !== m.role) rows.splice(i).forEach(destroyRow);
      if (!rows[i]) rows[i] = appendBubble(m.role);
      const key = (m.typing ? 'T|' : 'M|') + m.content;
      if (rows[i].key !== key) { rows[i].key = key; paint(rows[i], m); changed = true; }
    });
    sendBtn.disabled = !!pending;
    if (changed) requestAnimationFrame(() => { msgsEl.scrollTop = msgsEl.scrollHeight; window.dispatchEvent(new Event('resize')); });
  }

  /* ---------- model picker ---------- */
  const menu = $('#modelMenu');
  function renderModels() {
    menu.innerHTML = '';
    (A.models || []).forEach(m => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'model-item' + (m.id === S.model ? ' on' : ''); b.setAttribute('role', 'option');
      b.textContent = m.label;
      b.addEventListener('click', () => { S.model = m.id; renderModels(); closeMenus(); });
      menu.append(b);
    });
    const cur = (A.models || []).find(m => m.id === S.model);
    $('#modelLabel').textContent = cur ? cur.label : '';
  }
  function closeMenus() { menu.classList.remove('open'); panel.classList.remove('open'); $('#modelBtn').setAttribute('aria-expanded', 'false'); }
  $('#modelBtn').addEventListener('click', () => { const o = menu.classList.toggle('open'); panel.classList.remove('open'); $('#modelBtn').setAttribute('aria-expanded', o); });
  $('#gear').addEventListener('click', () => { const o = panel.classList.toggle('open'); if (o) menu.classList.remove('open'); });
  document.addEventListener('click', e => {
    if (!e.target.closest('#modelWrap')) menu.classList.remove('open');
    if (!panel.contains(e.target) && !e.target.closest('.gear-shell')) panel.classList.remove('open');
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenus(); });

  /* ---------- send ---------- */
  const fitTextarea = () => { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'; };
  function send() {
    const text = ta.value.trim();
    if (!text || pending) return;
    const id = pending = crypto.randomUUID();
    msgs = [...msgs, { role: 'user', content: text }];
    ta.value = ''; fitTextarea(); sync();
    post('setComponentValue', { value: { id, type: 'send', text, model: S.model }, dataType: 'json' });
    setTimeout(() => { if (pending === id) { pending = null; sync(); } }, 150000);
  }
  ta.addEventListener('input', fitTextarea);
  ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
  sendBtn.addEventListener('click', send);

  /* ---------- Streamlit component protocol ---------- */
  window.addEventListener('message', e => {
    if (!e.data || e.data.type !== 'streamlit:render') return;
    A = e.data.args || {};
    if (!pending || A.reply_to === pending) {
      msgs = A.messages || [];
      if (A.reply_to === pending) pending = null;
    }
    if (!booted) { booted = true; S.model = A.default_model; renderModels(); initGlass(); }
    statusEl.textContent = A.has_key ? '' : 'Add your API key to Streamlit secrets.';
    sync();
  });
  post('componentReady', { apiVersion: 1 });
  post('setFrameHeight', { height: 800 });
  fitTextarea();
})();
</script>
</body>
</html>
'''

_dir = Path(tempfile.gettempdir()) / ("lg_chat_" + hashlib.md5(UI_HTML.encode()).hexdigest()[:10])
_dir.mkdir(parents=True, exist_ok=True)
(_dir / "index.html").write_text(UI_HTML, encoding="utf-8")
_bg = Path(__file__).parent / "city.png"          # keep city.png next to app.py
if _bg.exists():
    shutil.copyfile(_bg, _dir / "city.png")
_ui = components.declare_component("liquid_glass_chat", path=str(_dir))

PROVIDERS = {
    "ollama": {"endpoint": "https://ollama.com", "model": "nemotron-3-nano:30b-cloud"},
    "openai": {"endpoint": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
}
MODELS = [
    {"label": "gemma4", "id": "gemma4:31b-cloud"},
    {"label": "nemotron-3-nano", "id": "nemotron-3-nano:30b-cloud"},
    {"label": "gpt-oss", "id": "gpt-oss:20b-cloud"},
]
DEFAULT_MODEL = "nemotron-3-nano:30b-cloud"
GEN = {"temperature": 0.7, "top_p": 1.0, "max_tokens": 2048}


def secret(section):
    try:
        return dict(st.secrets.get(section, {}))
    except Exception:
        return {}


def provider_name():
    p = secret("app").get("provider", "ollama")      # optional: set [app] provider = "openai"
    return p if p in PROVIDERS else "ollama"


def ask(model_id, history):
    name = provider_name()
    s, d = secret(name), PROVIDERS[name]
    endpoint = s.get("endpoint", d["endpoint"]).rstrip("/")
    u = urlparse(endpoint)
    if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1"))):
        raise ValueError("Endpoint must use https://")
    key = s.get("api_key", "")
    if not key:
        raise ValueError(f"Add api_key under [{name}] in Streamlit secrets.")
    system = secret("app").get("system", "You are a helpful assistant.")
    msgs = ([{"role": "system", "content": system}] if system else []) + history
    headers = {"Authorization": f"Bearer {key}"}

    if name == "ollama":
        model = model_id if model_id in {m["id"] for m in MODELS} else DEFAULT_MODEL
        names = [model] + ([model[:-6]] if model.endswith("-cloud") else [])   # retry without "-cloud" on 404
    else:
        names = [s.get("model", d["model"])]

    for i, model in enumerate(names):
        if name == "ollama":
            url = f"{endpoint}/api/chat"
            body = {"model": model, "messages": msgs, "stream": False,
                    "options": {"temperature": GEN["temperature"], "top_p": GEN["top_p"],
                                "num_predict": GEN["max_tokens"]}}
        else:
            url = f"{endpoint}/chat/completions"
            body = {"model": model, "messages": msgs, **GEN}
        r = requests.post(url, headers=headers, json=body, timeout=120)
        if r.status_code == 404 and i < len(names) - 1:
            continue
        break
    if not r.ok:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    j = r.json()
    return j["message"]["content"] if name == "ollama" else j["choices"][0]["message"]["content"]


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
          models=MODELS, default_model=DEFAULT_MODEL,
          has_key=bool(secret(provider_name()).get("api_key")),
          reply_to=st.session_state.seen,
          key="ui", default=None)

if val and val.get("id") != st.session_state.seen:
    st.session_state.seen = val["id"]
    st.session_state.msgs.append({"role": "user", "content": str(val.get("text", ""))[:20000]})
    history = [{"role": m["role"], "content": m["content"]}
               for m in st.session_state.msgs if not m.get("error")]
    try:
        out = {"role": "assistant", "content": ask(val.get("model"), history)}
    except Exception as e:
        out = {"role": "assistant", "content": f"⚠️ {e}", "error": True}
    st.session_state.msgs.append(out)
    st.rerun()

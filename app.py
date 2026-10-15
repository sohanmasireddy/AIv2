import hashlib
import hmac
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title AIv2", page_icon="💧", layout="wide",
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
:root{color-scheme:dark;--text:#f7f9fc;--muted:rgba(247,249,252,.67);--glass-border:rgba(255,255,255,.30);--glass-fill:rgba(231,241,255,.085)}
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
.glass-lens{position:absolute;inset:0;z-index:2;border:1px solid var(--glass-border);border-radius:inherit;background:var(--glass-fill);backdrop-filter:blur(22px) saturate(1.32);-webkit-backdrop-filter:blur(22px) saturate(1.32);pointer-events:none}
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

/* Attachments */
#attachments{position:relative;z-index:4;display:flex;flex-wrap:wrap;gap:7px;padding:0 8px 8px}
#attachments:empty{display:none}
.attachment-chip{display:flex;align-items:center;gap:8px;min-width:0;max-width:min(300px,100%);padding:6px 8px 6px 11px;border:1px solid rgba(255,255,255,.2);border-radius:999px;background:rgba(245,249,255,.12);color:rgba(255,255,255,.95);font-size:12px;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
.attachment-chip .file-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.attachment-chip .file-kind{opacity:.67;white-space:nowrap}
.attachment-chip button{display:grid;place-items:center;width:20px;height:20px;flex:none;border:0;border-radius:50%;background:rgba(255,255,255,.12);color:white;cursor:pointer;line-height:1}
.attachment-chip button:hover{background:rgba(255,255,255,.24)}
#fileInput{display:none}
.add-shell{flex:0 0 44px}
.add-shell .glass-lens{background:rgba(245,249,255,.10)}
#addFiles{font-size:24px;font-weight:350}

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
.attachment-chip{max-width:calc(100vw - 60px)}
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
      <div id="attachments" aria-live="polite" aria-label="Attached files"></div>
      <div class="composer-inner">
        <div class="round-shell add-shell">
          <div class="glass-lens" id="addGlass" aria-hidden="true"></div>
          <button class="round-btn" id="addFiles" type="button" aria-label="Add files" title="Add files">＋</button>
          <input id="fileInput" type="file" multiple accept="image/png,image/jpeg,image/webp,image/gif,.txt,.md,.csv,.json,.xml,.html,.css,.js,.ts,.py,.log,.yaml,.yml,.toml,.sql,.sh,.java,.c,.cpp,.h,.rs,.go,.rb,.php,.ini,.cfg,.env,.rst,.tex,.diff,.patch">
        </div>
        <textarea id="ta" rows="1" placeholder="Ask anything" aria-label="Message" autocomplete="off" spellcheck="true"></textarea>
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

  /* ---------- hide platform badge (best effort, same-origin frames only) ---------- */
  const BADGE = '[class*="viewerBadge"],[class*="profileContainer"],[class*="profilePreview"],a[href*="streamlit.io"]';
  function frames(w, out = []) { try { out.push(w.document); for (let i = 0; i < w.frames.length; i++) frames(w.frames[i], out); } catch (e) {} return out; }
  function hideBadge() {
    frames(window.top).forEach(d => { try {
      if (!d.getElementById('lg-hide')) { const s = d.createElement('style'); s.id = 'lg-hide'; s.textContent = BADGE + '{display:none!important}'; d.head.appendChild(s); }
    } catch (e) {} });
  }
  // One pass is enough; repeatedly scanning nested frames wastes work.
  hideBadge();

  /* ---------- liquid glass ---------- */
  const glassOptions = {
    snapshot: '#scene',
    // Force liquidGL's WebGPU backend where supported; do not choose WebGL.
    engine: 'webgpu', resolution: 2.5, zIndex: 2, content: false,
    refraction: 0.016, bevelDepth: 0.065, bevelWidth: 0.18,
    frost: 1.5, aberration: 0.002, magnify: 1,
    shadow: true, specular: true, tint: 'rgba(218,233,255,0.05)',
    reveal: 'none', interaction: 'none', draggable: false, tilt: false
  };
  // Only visible surface controls are inherited by new message lenses.
  const INHERIT = ['refraction','aberration','bevelDepth','bevelWidth','magnify','frost','specular','shadow'];

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

  // Keep visual tuning in Settings, but remove Interaction/Initialisation folders.
  function removeUnneededSettings(guiRoot) {
    if (!guiRoot) return;
    guiRoot.querySelectorAll('.lil-gui').forEach(folder => {
      if (folder === guiRoot) return;
      const title = folder.querySelector(':scope > .title');
      const label = (title?.textContent || '').trim();
      if (/^(interaction|initialisation|initialization)$/i.test(label)) folder.remove();
    });
  }
  function adoptGui(tries = 0) {
    const g = (window.__liquidGLHelperGUIs__ || [])[0];
    if (!g) { if (tries < 60) setTimeout(() => adoptGui(tries + 1), 100); return; }
    g.gui.open();
    panel.appendChild(g.gui.domElement);
    removeUnneededSettings(g.gui.domElement);
  }

  async function initGlass() {
    await $('#bgimg').decode().catch(() => {});
    try {
      await Promise.all([load(BASE + 'liquidGL.js'), load(BASE + 'liquidGL-helper.js')]);
      if (typeof window.liquidGL !== 'function') throw new Error('liquidGL did not load');
      glassReady = true;
      const first = ['#composerGlass', '#addGlass', '#sendGlass', '#gearGlass'].map(s => installLens($(s))).filter(Boolean);
      if (window.__liquidGLHelper__ && first.length) {
        window.__liquidGLHelper__(first, { ...glassOptions, target: '#composerGlass' });
        adoptGui();
      }
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
    if (changed) requestAnimationFrame(() => { msgsEl.scrollTop = msgsEl.scrollHeight; });
  }

  /* ---------- settings menu ---------- */
  function closeMenus() { panel.classList.remove('open'); }
  $('#gear').addEventListener('click', () => panel.classList.toggle('open'));
  document.addEventListener('click', e => {
    if (!panel.contains(e.target) && !e.target.closest('.gear-shell')) panel.classList.remove('open');
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenus(); });

  /* ---------- file attachments ---------- */
  const fileInput = $('#fileInput'), addFilesBtn = $('#addFiles'), attachmentsEl = $('#attachments');
  const attached = [];
  const TEXT_EXT = new Set(['txt','md','csv','json','xml','html','css','js','ts','py','log','yaml','yml','toml','sql','sh','java','c','cpp','h','rs','go','rb','php','ini','cfg','env','rst','tex','diff','patch']);
  const IMAGE_TYPES = new Set(['image/png','image/jpeg','image/webp','image/gif']);
  const MAX_FILES = 5, MAX_IMAGE_BYTES = 3 * 1024 * 1024, MAX_TEXT_BYTES = 150 * 1024, MAX_TOTAL_BYTES = 7 * 1024 * 1024, MAX_TEXT_CHARS = 100000;
  const extOf = name => (name.split('.').pop() || '').toLowerCase();
  function formatBytes(n) { return n < 1024 ? n + ' B' : n < 1048576 ? (n/1024).toFixed(0) + ' KB' : (n/1048576).toFixed(1) + ' MB'; }
  function renderAttachments() {
    attachmentsEl.replaceChildren();
    attached.forEach((file, idx) => {
      const chip = document.createElement('div'); chip.className = 'attachment-chip';
      const name = document.createElement('span'); name.className = 'file-name'; name.textContent = file.name; name.title = file.name;
      const kind = document.createElement('span'); kind.className = 'file-kind'; kind.textContent = file.kind === 'image' ? 'image' : 'file';
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×'; remove.setAttribute('aria-label', 'Remove ' + file.name); remove.title = 'Remove file';
      remove.addEventListener('click', () => { attached.splice(idx, 1); renderAttachments(); });
      chip.append(name, kind, remove); attachmentsEl.append(chip);
    });
  }
  function readDataURL(file) { return new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(String(r.result || '').split(',').pop()); r.onerror = () => reject(new Error('Could not read ' + file.name)); r.readAsDataURL(file); }); }
  addFilesBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', async () => {
    const incoming = Array.from(fileInput.files || []); fileInput.value = '';
    for (const file of incoming) {
      if (attached.length >= MAX_FILES) { statusEl.textContent = 'You can attach up to ' + MAX_FILES + ' files per message.'; break; }
      if (attached.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) continue;
      const ext = extOf(file.name), isImage = IMAGE_TYPES.has(file.type), isText = TEXT_EXT.has(ext) || file.type.startsWith('text/') || file.type === 'application/json';
      if (!isImage && !isText) { statusEl.textContent = 'Unsupported file type: ' + file.name + '. Choose an image or a text/code file.'; continue; }
      if (isImage && file.size > MAX_IMAGE_BYTES) { statusEl.textContent = file.name + ' is too large. Images must be 3 MB or smaller.'; continue; }
      if (isText && file.size > MAX_TEXT_BYTES) { statusEl.textContent = file.name + ' is too large. Text files must be 150 KB or smaller.'; continue; }
      const currentBytes = attached.reduce((sum, f) => sum + f.size, 0);
      if (currentBytes + file.size > MAX_TOTAL_BYTES) { statusEl.textContent = 'Attachments must total 7 MB or less.'; break; }
      try {
        if (isImage) {
          attached.push({name:file.name,type:file.type,kind:'image',data:await readDataURL(file),size:file.size,lastModified:file.lastModified});
        } else {
          const data = await file.text();
          if (data.length > MAX_TEXT_CHARS) { statusEl.textContent = file.name + ' contains too much text (100,000 characters maximum).'; continue; }
          attached.push({name:file.name,type:file.type || 'text/plain',kind:'text',data,size:file.size,lastModified:file.lastModified});
        }
        renderAttachments();
        statusEl.textContent = '';
      } catch (err) { statusEl.textContent = err.message || 'Could not read that file.'; }
    }
  });

  /* ---------- send ---------- */
  const fitTextarea = () => { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'; };
  function send() {
    const text = ta.value.trim();
    if ((!text && !attached.length) || pending) return;
    const id = pending = crypto.randomUUID();
    const files = attached.map(({name,type,kind,data,size}) => ({name,type,kind,data,size}));
    const visible = [text, ...files.map(f => '📎 ' + f.name)].filter(Boolean).join('\n\n');
    msgs = [...msgs, { role: 'user', content: visible }];
    attached.splice(0, attached.length); renderAttachments();
    ta.value = ''; fitTextarea(); sync();
    post('setComponentValue', { value: { id, type: 'send', text, attachments: files }, dataType: 'json' });
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
    if (!booted) { booted = true; initGlass(); }
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
    "ollama": {"endpoint": "https://ollama.com", "model": "gemma4:31b-cloud"},
    "openai": {"endpoint": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
}
DEFAULT_MODEL = "gemma4:31b-cloud"
GEN = {"temperature": 0.7, "top_p": 1.0, "max_tokens": 2048}


def secret(section):
    try:
        return dict(st.secrets.get(section, {}))
    except Exception:
        return {}


def provider_name():
    p = secret("app").get("provider", "ollama")      # optional: set [app] provider = "openai"
    return p if p in PROVIDERS else "ollama"


def ask(history):
    """Call the configured chat API using fixed Gemma 4 by default.

    Text attachments are included in the user's prompt. Images are retained in
    the history and sent using each provider's supported message format.
    """
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
    source_messages = ([{"role": "system", "content": system}] if system else []) + history
    headers = {"Authorization": f"Bearer {key}"}

    if name == "ollama":
        model = DEFAULT_MODEL
        names = [model] + ([model[:-6]] if model.endswith("-cloud") else [])
        messages = []
        for m in source_messages:
            item = {"role": m["role"], "content": m.get("content", "")}
            images = m.get("images") or []
            if images:
                item["images"] = [im["data"] for im in images]
            messages.append(item)
    else:
        names = [s.get("model", d["model"])]
        messages = []
        for m in source_messages:
            content = m.get("content", "")
            images = m.get("images") or []
            if images:
                parts = [{"type": "text", "text": content}]
                for im in images:
                    parts.append({"type": "image_url", "image_url": {
                        "url": f"data:{im['type']};base64,{im['data']}"
                    }})
                content = parts
            messages.append({"role": m["role"], "content": content})

    for i, model in enumerate(names):
        if name == "ollama":
            url = f"{endpoint}/api/chat"
            body = {"model": model, "messages": messages, "stream": False,
                    "options": {"temperature": GEN["temperature"], "top_p": GEN["top_p"],
                                "num_predict": GEN["max_tokens"]}}
        else:
            url = f"{endpoint}/chat/completions"
            body = {"model": model, "messages": messages, **GEN}
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
st.session_state.setdefault("api_history", [])
st.session_state.setdefault("seen", None)

val = _ui(messages=st.session_state.msgs,
          default_model=DEFAULT_MODEL,
          has_key=bool(secret(provider_name()).get("api_key")),
          reply_to=st.session_state.seen,
          key="ui", default=None)

if val and val.get("id") != st.session_state.seen:
    st.session_state.seen = val["id"]
    user_text = str(val.get("text", ""))[:20000].strip()
    raw_attachments = val.get("attachments", [])
    if not isinstance(raw_attachments, list):
        raw_attachments = []
    raw_attachments = raw_attachments[:5]
    api_content_parts = [user_text] if user_text else []
    image_attachments = []
    display_files = []
    total_attachment_bytes = 0
    allowed_images = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    allowed_text_exts = {"txt", "md", "csv", "json", "xml", "html", "css", "js", "ts", "py", "log", "yaml", "yml", "toml", "sql", "sh", "java", "c", "cpp", "h", "rs", "go", "rb", "php", "ini", "cfg", "env", "rst", "tex", "diff", "patch"}
    for item in raw_attachments:
        if not isinstance(item, dict):
            continue
        file_name = str(item.get("name", "attachment"))[:200]
        mime = str(item.get("type", "application/octet-stream"))[:100]
        kind = item.get("kind")
        data = item.get("data", "")
        if not isinstance(data, str):
            continue
        if kind == "image" and mime in allowed_images:
            # Base64 data is checked and size-limited before it reaches the API.
            if len(data) > 4_300_000:
                continue
            try:
                import base64
                decoded = base64.b64decode(data, validate=True)
            except Exception:
                continue
            total_attachment_bytes += len(decoded)
            if total_attachment_bytes > 7 * 1024 * 1024:
                continue
            image_attachments.append({"name": file_name, "type": mime, "data": data})
            display_files.append(file_name)
        elif kind == "text":
            ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
            if ext not in allowed_text_exts or len(data) > 100_000:
                continue
            total_attachment_bytes += len(data.encode("utf-8", errors="replace"))
            if total_attachment_bytes > 7 * 1024 * 1024:
                continue
            api_content_parts.append(f"\n\n[Attached file: {file_name}]\n```\n{data}\n```")
            display_files.append(file_name)
    api_content = "".join(api_content_parts).strip()
    if not api_content:
        api_content = "Please analyze the attached file(s)." if image_attachments else "Please review the attached file(s)."
    display_content = "\n\n".join(([user_text] if user_text else []) + ["📎 " + n for n in display_files])
    if not display_content:
        display_content = user_text or "Please review the attached file(s)."
    st.session_state.msgs.append({"role": "user", "content": display_content})
    st.session_state.api_history.append({"role": "user", "content": api_content, "images": image_attachments})
    try:
        answer = ask(st.session_state.api_history)
        out = {"role": "assistant", "content": answer}
        st.session_state.api_history.append({"role": "assistant", "content": answer})
    except Exception as e:
        out = {"role": "assistant", "content": f"⚠️ {e}", "error": True}
    st.session_state.msgs.append(out)
    st.rerun()

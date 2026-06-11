const STORAGE_KEY = "lyrics_operator_api_base";
const TRANSLATE_KEY = "lyrics_operator_translate_base";
const LOCAL_IMPORT_KEY = "lyrics_operator_local_import";

const $ = (id) => document.getElementById(id);

let selectedLink = null;
let lastFetch = null;
let ewImportAvailable = false;
let translatedActive = false;

function initLocalImportFromQuery() {
  const q = new URLSearchParams(location.search).get("localImport");
  if (q) {
    localStorage.setItem(LOCAL_IMPORT_KEY, q.trim().replace(/\/$/, ""));
  }
}

/** Base URL for local import API (desktop or import_server.py). Empty = same origin. */
function localImportBase() {
  const saved = localStorage.getItem(LOCAL_IMPORT_KEY);
  if (saved) return saved.replace(/\/$/, "");
  const host = location.hostname;
  if (host !== "localhost" && host !== "127.0.0.1") return "";
  // Dev: UI on :3001, import on :3000 (serve_ui.py + import_server.py)
  if (location.port && location.port !== "3000") {
    return "http://127.0.0.1:3000";
  }
  return "";
}

function localImportUrl(path) {
  const base = localImportBase();
  return base ? `${base}${path}` : path;
}

/** Native pywebview bridge when running inside the desktop window. */
function desktopApi() {
  if (typeof window === "undefined") return null;
  const api = window.pywebview && window.pywebview.api;
  return api && typeof api.save_text === "function" ? api : null;
}

function isLocalHost() {
  const host = location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

/** Dev: separate localhost ports. Prod: same-origin paths behind the reverse proxy. */
function defaultApiBase() {
  return isLocalHost() ? "http://localhost:8000" : "/api";
}

function defaultTranslateBase() {
  return isLocalHost() ? "http://localhost:8100" : "/translate";
}

function apiBase() {
  const raw = $("api-base").value.trim().replace(/\/$/, "");
  return raw || defaultApiBase();
}

function saveApiBase() {
  localStorage.setItem(STORAGE_KEY, apiBase());
}

function translateBase() {
  const raw = $("translate-base").value.trim().replace(/\/$/, "");
  return raw || defaultTranslateBase();
}

function saveTranslateBase() {
  localStorage.setItem(TRANSLATE_KEY, translateBase());
}

/** The lyrics currently shown (translated when toggled on), used by copy/download/import. */
function activeLyricsText() {
  if (!lastFetch) return "";
  if (translatedActive && lastFetch.lyrics_translated) return lastFetch.lyrics_translated;
  return lastFetch.lyrics_plain || "";
}

function renderLyrics() {
  const out = $("lyrics-output");
  out.textContent = activeLyricsText();
  out.classList.remove("empty");
  const btn = $("btn-translate");
  if (translatedActive) {
    btn.textContent = "Show original";
  } else if (lastFetch?.lyrics_translated) {
    btn.textContent = "Show translation";
  } else {
    btn.textContent = "Translate";
  }
}

function hostLabel(url) {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    if (host.includes("azlyrics.com")) return { text: "AZLyrics", className: "host-az" };
    if (host === "genius.com") return { text: "Genius", className: "host-genius" };
    return { text: host, className: "" };
  } catch {
    return { text: "link", className: "" };
  }
}

async function checkHealth() {
  const badge = $("health-badge");
  badge.textContent = "…";
  badge.className = "badge badge-muted";
  try {
    const res = await fetch(`${apiBase()}/healthz`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const parts = ["ok"];
    if (data.genius_configured) parts.push("Genius");
    if (data.gemini_configured) parts.push("Gemini");
    badge.textContent = parts.join(" · ");
    badge.className = "badge badge-ok";
    badge.title = `Gemini: ${data.gemini_configured}, Genius: ${data.gemini_configured}`;
  } catch (err) {
    badge.textContent = "offline";
    badge.className = "badge badge-warn";
    badge.title = String(err.message || err);
  }
}

function formatApiError(detail) {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const parts = [detail.message, detail.error, detail.primary_error].filter(Boolean);
    return parts.join(" — ") || JSON.stringify(detail, null, 2);
  }
  return "Request failed";
}

async function apiPost(path, body) {
  const res = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(formatApiError(data.detail ?? data));
  }
  return data;
}

function renderLinks(links) {
  const list = $("links-list");
  list.innerHTML = "";
  if (!links.length) {
    list.innerHTML = '<li class="status">No lyric-site links found. Try a longer snippet.</li>';
    return;
  }
  for (const item of links) {
    const li = document.createElement("li");
    li.className = "link-item";
    const host = hostLabel(item.link);
    const inner = document.createElement("div");
    inner.className = "link-item-inner";
    const selectBtn = document.createElement("button");
    selectBtn.type = "button";
    selectBtn.className = "link-select-btn";
    selectBtn.innerHTML = `
      <span class="link-title">${escapeHtml(item.title || item.link)}</span>
      <span class="link-snippet">${escapeHtml(item.snippet || "")}</span>
      <span class="link-host ${host.className}">${escapeHtml(host.text)}</span>
    `;
    selectBtn.addEventListener("click", () => selectLink(item, li));
    const openA = document.createElement("a");
    openA.className = "link-open-btn";
    openA.href = item.link;
    openA.target = "_blank";
    openA.rel = "noopener";
    openA.textContent = "Open";
    inner.append(selectBtn, openA);
    li.appendChild(inner);
    list.appendChild(li);
  }
  clearSelection();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function clearSelection() {
  selectedLink = null;
  $("btn-fetch").disabled = true;
  const openSel = $("selected-open-url");
  openSel.classList.add("hidden");
  openSel.href = "#";
  $("selected-label").textContent = "No link selected.";
}

function selectLink(item, liEl) {
  document.querySelectorAll(".link-item").forEach((el) => el.classList.remove("selected"));
  liEl.classList.add("selected");
  selectedLink = item;
  $("btn-fetch").disabled = false;
  const openSel = $("selected-open-url");
  openSel.href = item.link;
  openSel.classList.remove("hidden");
  $("selected-label").textContent = item.title || item.link;
  $("fetch-status").textContent = "";
  $("fetch-status").className = "status";
}

async function runIdentify() {
  const snippet = $("snippet").value.trim();
  const status = $("identify-status");
  const btn = $("btn-identify");
  if (snippet.length < 2) {
    status.textContent = "Enter at least 2 characters.";
    status.className = "status error";
    return;
  }
  btn.disabled = true;
  status.textContent = "Searching…";
  status.className = "status";
  $("links-list").innerHTML = "";
  clearSelection();
  resetLyricsPanel("Select a link, then click Fetch lyrics.");
  try {
    saveApiBase();
    const data = await apiPost("/v1/identify", {
      lyrics_snippet: snippet,
      max_results: Number($("max-results").value) || 10,
    });
    renderLinks(data.links || []);
    status.textContent = `${(data.links || []).length} link(s) · session ${data.session_id?.slice(0, 8) ?? ""}`;
    status.className = "status ok";
  } catch (err) {
    status.textContent = err.message;
    status.className = "status error";
  } finally {
    btn.disabled = false;
  }
}

function resetLyricsPanel(message) {
  lastFetch = null;
  $("fetch-meta").classList.add("hidden");
  $("fetch-actions").classList.add("hidden");
  const out = $("lyrics-output");
  out.textContent = message;
  out.classList.add("empty");
}

function provenanceLabel(prov) {
  if (!prov) return "unknown";
  let label = prov.source;
  if (prov.fallback_used) label += " (fallback)";
  if (prov.primary_error) label += ` · was: ${prov.primary_error}`;
  return label;
}

async function fetchLyrics(url) {
  const status = $("fetch-status");
  status.textContent = "Fetching lyrics…";
  status.className = "status";
  resetLyricsPanel("Loading…");
  $("fetch-actions").classList.add("hidden");
  try {
    const data = await apiPost("/v1/lyrics/fetch", { url });
    lastFetch = { ...data, url, lyrics_translated: null };
    translatedActive = false;
    $("song-title").textContent = data.title || "Unknown Title";
    $("song-author").textContent = data.author ? `· ${data.author}` : "";
    const badge = $("provenance-badge");
    badge.textContent = provenanceLabel(data.provenance);
    badge.className = data.provenance?.fallback_used ? "badge badge-warn" : "badge badge-ok";
    $("open-url").href = url;
    renderLyrics();
    $("fetch-meta").classList.remove("hidden");
    $("fetch-actions").classList.remove("hidden");
    await checkLocalCapabilities();
    status.textContent = ewImportAvailable
      ? "Lyrics loaded. Review before importing to EasyWorship."
      : "Lyrics loaded. Use copy/download, or run import on Windows (desktop.py).";
    status.className = "status ok";
  } catch (err) {
    status.textContent = err.message;
    status.className = "status error";
    resetLyricsPanel("Fetch failed. Try another link (AZ or Genius preferred).");
  }
}

function safeFilename(title) {
  const base = (title || "song")
    .replace(/[<>:"/\\|?*]/g, "")
    .trim()
    .slice(0, 80);
  return `${base || "song"}.txt`;
}

async function downloadEwFile() {
  if (!lastFetch) return;
  const status = $("fetch-status");
  const body = activeLyricsText();
  const filename = safeFilename(lastFetch.title);

  const api = desktopApi();
  if (api) {
    try {
      const res = await api.save_text(filename, body);
      if (res?.cancelled) return;
      if (res?.ok) {
        status.textContent = `Saved: ${res.path}`;
        status.className = "status ok";
      } else {
        status.textContent = res?.message || "Save failed.";
        status.className = "status error";
      }
    } catch (err) {
      status.textContent = String(err?.message || err);
      status.className = "status error";
    }
    return;
  }

  const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function copyViaTextarea(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.top = "-1000px";
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  document.body.removeChild(ta);
  return ok;
}

async function copyLyrics() {
  if (!lastFetch) return;
  const status = $("fetch-status");
  const text = activeLyricsText();
  if (!text) return;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else if (!copyViaTextarea(text)) {
      throw new Error("Clipboard not available.");
    }
    status.textContent = "Copied to clipboard.";
    status.className = "status ok";
  } catch {
    if (copyViaTextarea(text)) {
      status.textContent = "Copied to clipboard.";
      status.className = "status ok";
    } else {
      status.textContent = "Copy failed — select the text and press Ctrl+C.";
      status.className = "status error";
    }
  }
}

function setImportUi(available) {
  ewImportAvailable = available;
  const btn = $("btn-import");
  if (available) {
    btn.classList.remove("hidden");
    btn.disabled = false;
    $("hint-desktop").classList.remove("hidden");
    $("hint-cli").classList.add("hidden");
  } else {
    btn.classList.add("hidden");
    btn.disabled = true;
    $("hint-desktop").classList.add("hidden");
    $("hint-cli").classList.remove("hidden");
  }
}

async function checkLocalCapabilities() {
  const base = localImportBase();
  const host = location.hostname;
  if (!base && host !== "localhost" && host !== "127.0.0.1") {
    setImportUi(false);
    return;
  }
  const url = localImportUrl("/local/capabilities");
  try {
    const res = await fetch(url);
    if (!res.ok) {
      setImportUi(false);
      return;
    }
    const data = await res.json();
    setImportUi(Boolean(data.easyworship_import));
  } catch {
    setImportUi(false);
  }
}

async function importToEasyWorship() {
  if (!lastFetch || !ewImportAvailable) return;
  const lyrics = activeLyricsText();
  if (!lyrics) return;

  const status = $("fetch-status");
  const btn = $("btn-import");
  btn.disabled = true;
  status.textContent = "Importing to EasyWorship…";
  status.className = "status";

  try {
    const res = await fetch(localImportUrl("/local/import"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lyrics_plain: lyrics,
        title: lastFetch.title || "",
        author: lastFetch.author || "",
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      const parts = [data.message || "Import failed."];
      if (data.output) parts.push(data.output);
      throw new Error(parts.join("\n"));
    }
    status.textContent =
      (data.message || "Import OK.") +
      " Refresh EasyWorship; run Rebuild Search Keys (Profiles > Utilities) for lyric search.";
    status.className = "status ok";
  } catch (err) {
    status.textContent = err.message;
    status.className = "status error";
  } finally {
    btn.disabled = false;
  }
}

async function checkTranslateHealth() {
  const badge = $("translate-badge");
  badge.textContent = "…";
  badge.className = "badge badge-muted";
  try {
    const res = await fetch(`${translateBase()}/healthz`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    badge.textContent = data.gemini_configured ? "ok" : "no key";
    badge.className = data.gemini_configured ? "badge badge-ok" : "badge badge-warn";
    badge.title = `model: ${data.model || "?"}`;
  } catch (err) {
    badge.textContent = "offline";
    badge.className = "badge badge-warn";
    badge.title = String(err.message || err);
  }
}

async function translateLyrics() {
  if (!lastFetch?.lyrics_plain) return;
  const status = $("fetch-status");
  const btn = $("btn-translate");

  // Already have a translation -> just toggle the view.
  if (lastFetch.lyrics_translated) {
    translatedActive = !translatedActive;
    renderLyrics();
    return;
  }

  btn.disabled = true;
  status.textContent = "Translating non-English lines…";
  status.className = "status";
  try {
    const res = await fetch(`${translateBase()}/v1/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lyrics_plain: lastFetch.lyrics_plain, target_lang: "en" }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(formatApiError(data.detail ?? data));
    }
    lastFetch.lyrics_translated = data.lyrics_translated || lastFetch.lyrics_plain;
    translatedActive = true;
    renderLyrics();
    status.textContent = data.lines_translated
      ? `Translated ${data.lines_translated} line(s).`
      : "No non-English lines found.";
    status.className = "status ok";
  } catch (err) {
    status.textContent = err.message;
    status.className = "status error";
  } finally {
    btn.disabled = false;
  }
}

function initExternalLinks() {
  document.addEventListener("click", (e) => {
    const api = desktopApi();
    if (!api?.open_external) return;
    const a = e.target.closest?.("a[href]");
    if (!a) return;
    const href = a.getAttribute("href");
    if (!href || href === "#" || !/^https?:/i.test(href)) return;
    e.preventDefault();
    api.open_external(href);
  });
}

function init() {
  initLocalImportFromQuery();
  setImportUi(false);
  initExternalLinks();
  $("api-base").value = localStorage.getItem(STORAGE_KEY) || defaultApiBase();
  $("translate-base").value = localStorage.getItem(TRANSLATE_KEY) || defaultTranslateBase();

  $("api-base").addEventListener("change", () => {
    saveApiBase();
    checkHealth();
  });
  $("translate-base").addEventListener("change", () => {
    saveTranslateBase();
    checkTranslateHealth();
  });

  $("btn-identify").addEventListener("click", runIdentify);
  $("snippet").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      runIdentify();
    }
  });
  $("btn-fetch").addEventListener("click", () => {
    if (selectedLink?.link) fetchLyrics(selectedLink.link);
  });
  $("btn-copy").addEventListener("click", copyLyrics);
  $("btn-download").addEventListener("click", downloadEwFile);
  $("btn-translate").addEventListener("click", translateLyrics);
  $("btn-import").addEventListener("click", importToEasyWorship);

  checkHealth();
  checkTranslateHealth();
  checkLocalCapabilities();
}

init();

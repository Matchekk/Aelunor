let CAMPAIGN = null;
let SESSION = loadSession();
let SESSION_LIBRARY = loadSessionLibrary();
let CURRENT_ACTION_TYPE = "do";
let IS_SENDING_TURN = false;
let EDIT_TURN_ID = null;
let EDITING_STORY_CARD_ID = null;
let EDITING_WORLD_INFO_ID = null;
let SESSION_MODAL_ID = null;
let SETUP_FLOW = { mode: null, slotId: null, stack: [], index: -1 };
let PENDING_REQUESTS = 0;
let LOADING_TIMER = null;
let CHARACTER_SHEET = null;
let NPC_SHEET = null;
let CODEX_SHEET = null;
let DRAWER_MODE = "pc";
let ACTIVE_DRAWER_TAB = "overview";
let ACTIVE_SIDEBAR_TAB = "chars";
let ACTIVE_CODEX_TAB = "npcs";
let ACTIVE_SETTINGS_TAB = "session";
let CURRENT_THEME = loadTheme();
let CURRENT_FONT_PRESET = loadFontPreset();
let CURRENT_FONT_SIZE = loadFontSize();
let LAST_STORY_SCROLL_CAMPAIGN_ID = null;
let SETUP_RANDOM_STATE = { mode: "single", previewAnswers: [], previewTexts: [], questionId: null };
let LIVE_STATE = {
  activitiesByPlayer: {},
  blockingAction: null,
  sseConnected: false,
  version: 0,
  eventSource: null,
  campaignId: null,
  localLoadingVisible: false,
  localLoadingMessage: "Einen Moment bitte.",
  reconnectNeedsReload: false,
  reloadTimer: null,
  typingTimer: null,
  setupTimer: null,
  editTimer: null,
  highlightTurnId: null,
  highlightTimer: null,
};
let PARTY_HUD_PREV = {};
const NOVELTY_STORAGE_KEY = "isekaiNoveltyState";
let NOVELTY_STATE = loadNoveltyState();
const CONTINUE_STORY_MARKER = "__CONTINUE_STORY__";

const ACTION_MODE_CONFIG = {
  do: { label: "TUN", placeholder: "Was tut deine Figur konkret?" },
  say: { label: "SAGEN", placeholder: "Was sagt deine Figur?" },
  story: { label: "STORY", placeholder: "Welche Story-Richtung oder welchen Fokus willst du setzen?" },
  canon: { label: "CANON", placeholder: "Welcher Fakt soll direkt kanonisch in den Zustand übernommen werden?" },
  context: { label: "KONTEXT", placeholder: "Welche Frage hast du zur aktuellen Lage, Figuren oder Welt?" }
};

const SIDEBAR_TAB_IDS = ["chars", "diary", "map", "events"];
const SETTINGS_TAB_IDS = ["style", "plot", "note", "cards", "world", "memory", "session"];
const TAB_IDS = [...SETTINGS_TAB_IDS, ...SIDEBAR_TAB_IDS];
const DRAWER_PANEL_IDS = ["overview", "class", "attributes", "skills", "injuries", "gear"];
const PC_DRAWER_TABS = [
  { id: "overview", label: "Übersicht" },
  { id: "class", label: "Klasse" },
  { id: "attributes", label: "Attribute" },
  { id: "skills", label: "Skills" },
  { id: "injuries", label: "Injuries & Scars" },
  { id: "gear", label: "Inventar" }
];
const NPC_DRAWER_TABS = [
  { id: "overview", label: "Profil" },
  { id: "class", label: "Motiv & Ziel" },
  { id: "attributes", label: "Historie" },
  { id: "skills", label: "Bezüge" }
];
const CODEX_DRAWER_TABS = [
  { id: "overview", label: "Übersicht" },
  { id: "class", label: "Identität" },
  { id: "attributes", label: "Herkunft" },
  { id: "skills", label: "Stärken/Schwächen" },
  { id: "injuries", label: "Fähigkeiten" },
  { id: "gear", label: "Lore" }
];
const RACE_CODEX_BLOCK_ORDER = [
  "identity",
  "appearance",
  "culture",
  "homeland",
  "class_affinities",
  "skill_affinities",
  "strengths",
  "weaknesses",
  "relations",
  "notable_individuals"
];
const BEAST_CODEX_BLOCK_ORDER = [
  "identity",
  "appearance",
  "habitat",
  "behavior",
  "combat_style",
  "known_abilities",
  "strengths",
  "weaknesses",
  "loot",
  "lore"
];
const VALID_THEMES = ["arcane", "tavern", "glade", "hybrid"];
const THEME_LABELS = {
  arcane: "Nachtblau",
  tavern: "Taverne",
  glade: "Waldlichtung",
  hybrid: "Isekai (Hybrid)"
};

const FONT_PRESET_LABELS = {
  classic: "Standard",
  clean: "Klar",
  literary: "Roman"
};

const FONT_SIZE_LABELS = {
  small: "Klein",
  medium: "Mittel",
  large: "Groß"
};

const AGE_STAGE_LABELS = {
  teen: "Jugendlich",
  young: "Jung",
  adult: "Erwachsen",
  older: "Älter"
};

const BUILD_LABELS = {
  frail: "Schmächtig",
  lean: "Drahtig",
  neutral: "Ausgeglichen",
  robust: "Robust",
  broad: "Breit gebaut"
};

const AURA_LABELS = {
  none: "Keine",
  faint: "Schwach",
  grim: "Düster",
  dark: "Dunkel",
  ominous: "Unheilvoll",
  abyssal: "Abgründig"
};

const ENCUMBRANCE_LABELS = {
  normal: "Normal",
  burdened: "Belastet",
  overloaded: "Überladen"
};

const APPEARANCE_EVENT_LABELS = {
  stat_threshold: "Werteschwelle",
  corruption_threshold: "Verderbnisschwelle",
  faction_visual: "Fraktionsspur",
  class_visual: "Klassenspur",
  scar_added: "Neue Narbe",
  aging_stage: "Altersstufe",
  manual_story_mark: "Story-Merkmal"
};

function el(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return (value ?? "")
    .toString()
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function loadSession() {
  return {
    campaignId: localStorage.getItem("isekaiCampaignId"),
    playerId: localStorage.getItem("isekaiPlayerId"),
    playerToken: localStorage.getItem("isekaiPlayerToken"),
    joinCode: localStorage.getItem("isekaiJoinCode")
  };
}

function saveSession(session) {
  SESSION = session;
  localStorage.setItem("isekaiCampaignId", session.campaignId || "");
  localStorage.setItem("isekaiPlayerId", session.playerId || "");
  localStorage.setItem("isekaiPlayerToken", session.playerToken || "");
  localStorage.setItem("isekaiJoinCode", session.joinCode || "");
}

function clearSession() {
  SESSION = { campaignId: null, playerId: null, playerToken: null, joinCode: null };
  localStorage.removeItem("isekaiCampaignId");
  localStorage.removeItem("isekaiPlayerId");
  localStorage.removeItem("isekaiPlayerToken");
  localStorage.removeItem("isekaiJoinCode");
}

function loadSessionLibrary() {
  try {
    const raw = localStorage.getItem("isekaiSessionLibrary");
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function loadNoveltyState() {
  try {
    const raw = localStorage.getItem(NOVELTY_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed;
  } catch {
    return {};
  }
}

function saveNoveltyState() {
  localStorage.setItem(NOVELTY_STORAGE_KEY, JSON.stringify(NOVELTY_STATE || {}));
}

function noveltyBucket(campaignId, create = false) {
  const id = String(campaignId || "").trim();
  if (!id) return null;
  let bucket = NOVELTY_STATE[id];
  if (!bucket && create) {
    bucket = { items: {} };
    NOVELTY_STATE[id] = bucket;
  }
  if (!bucket || typeof bucket !== "object") return null;
  if (!bucket.items || typeof bucket.items !== "object" || Array.isArray(bucket.items)) {
    if (!create) return null;
    bucket.items = {};
  }
  return bucket;
}

function noveltyCount(campaignId, key) {
  const bucket = noveltyBucket(campaignId, false);
  if (!bucket) return 0;
  const value = Number((bucket.items || {})[key] || 0);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

function noveltyLabel(campaignId, key) {
  const count = noveltyCount(campaignId, key);
  if (!count) return "";
  return count > 1 ? `+${count}` : "Neu";
}

function noveltyMarkerMarkup(campaignId, key, compact = false) {
  const label = noveltyLabel(campaignId, key);
  if (!label) return "";
  return `<span class="new-marker ${compact ? "compact" : ""}" title="Ungelesene Änderung">${escapeHtml(label)}</span>`;
}

function noveltyMarkerForCount(count, compact = false) {
  const value = Math.max(0, Number(count || 0));
  if (!value) return "";
  const label = value > 1 ? `+${Math.floor(value)}` : "Neu";
  return `<span class="new-marker ${compact ? "compact" : ""}" title="Ungelesene Änderung">${escapeHtml(label)}</span>`;
}

function noveltyCountByPrefix(campaignId, prefix) {
  const bucket = noveltyBucket(campaignId, false);
  if (!bucket) return 0;
  return Object.entries(bucket.items || {}).reduce((acc, [key, value]) => {
    if (!String(key).startsWith(prefix)) return acc;
    const n = Number(value || 0);
    return acc + (Number.isFinite(n) && n > 0 ? Math.floor(n) : 0);
  }, 0);
}

function addNovelty(campaignId, key, amount = 1) {
  const id = String(campaignId || "").trim();
  const normalizedKey = String(key || "").trim();
  const inc = Math.max(1, Number(amount || 1));
  if (!id || !normalizedKey) return;
  const bucket = noveltyBucket(id, true);
  const current = noveltyCount(id, normalizedKey);
  bucket.items[normalizedKey] = current + inc;
  saveNoveltyState();
}

function clearNovelty(campaignId, key) {
  const bucket = noveltyBucket(campaignId, false);
  const normalizedKey = String(key || "").trim();
  if (!bucket || !normalizedKey || !(normalizedKey in (bucket.items || {}))) return false;
  delete bucket.items[normalizedKey];
  saveNoveltyState();
  return true;
}

function normalizeRank(rank) {
  const value = String(rank || "F").trim().toUpperCase();
  return ["F", "E", "D", "C", "B", "A", "S"].includes(value) ? value : "F";
}

function rankValue(rank) {
  const order = { F: 1, E: 2, D: 3, C: 4, B: 5, A: 6, S: 7 };
  return order[normalizeRank(rank)] || 1;
}

function injuryIdentity(entry, index) {
  if (!entry || typeof entry !== "object") return `inj_${index}`;
  const primary = String(entry.id || entry.title || entry.name || "").trim();
  if (primary) return primary.toLowerCase();
  const fallback = `${String(entry.severity || "").trim()}|${String(entry.healing_stage || "").trim()}|${index}`;
  return fallback.toLowerCase();
}

function trackCampaignNovelty(previousCampaign, nextCampaign) {
  const previousId = previousCampaign?.campaign_meta?.campaign_id || "";
  const nextId = nextCampaign?.campaign_meta?.campaign_id || "";
  if (!previousId || !nextId || previousId !== nextId) return;
  const campaignId = nextId;

  const prevChars = previousCampaign?.state?.characters || {};
  const nextChars = nextCampaign?.state?.characters || {};
  Object.entries(nextChars).forEach(([slotId, nextChar]) => {
    const prevChar = prevChars?.[slotId] || {};
    const prevSkills = prevChar?.skills || {};
    const nextSkills = nextChar?.skills || {};
    const newSkillCount = Object.keys(nextSkills).filter((skillId) => !prevSkills[skillId]).length;
    if (newSkillCount > 0) addNovelty(campaignId, `skill:${slotId}`, newSkillCount);

    const prevClass = prevChar?.class_current || null;
    const nextClass = nextChar?.class_current || null;
    if (nextClass && !prevClass) {
      addNovelty(campaignId, `class:${slotId}`, 1);
    } else if (nextClass && prevClass) {
      const prevLevel = Number(prevClass.level || 1);
      const nextLevel = Number(nextClass.level || 1);
      if (nextLevel > prevLevel) addNovelty(campaignId, `class:${slotId}`, Math.floor(nextLevel - prevLevel));
      if (rankValue(nextClass.rank) > rankValue(prevClass.rank)) addNovelty(campaignId, `class:${slotId}`, 1);
    }

    const prevInjuries = new Set((prevChar?.injuries || []).map((entry, index) => injuryIdentity(entry, index)));
    const nextInjuries = (nextChar?.injuries || []).map((entry, index) => injuryIdentity(entry, index));
    const newInjuryCount = nextInjuries.filter((id) => !prevInjuries.has(id)).length;
    if (newInjuryCount > 0) addNovelty(campaignId, `injury:${slotId}`, newInjuryCount);
  });

  const prevCodex = previousCampaign?.state?.codex || {};
  const nextCodex = nextCampaign?.state?.codex || {};
  const prevRaceCodex = prevCodex?.races || {};
  const nextRaceCodex = nextCodex?.races || {};
  Object.entries(nextRaceCodex).forEach(([raceId, nextEntry]) => {
    const prevLevel = Number(prevRaceCodex?.[raceId]?.knowledge_level || 0);
    const nextLevel = Number(nextEntry?.knowledge_level || 0);
    if (nextLevel > prevLevel) addNovelty(campaignId, `codex:race:${raceId}`, Math.floor(nextLevel - prevLevel));
  });
  const prevBeastCodex = prevCodex?.beasts || {};
  const nextBeastCodex = nextCodex?.beasts || {};
  Object.entries(nextBeastCodex).forEach(([beastId, nextEntry]) => {
    const prevLevel = Number(prevBeastCodex?.[beastId]?.knowledge_level || 0);
    const nextLevel = Number(nextEntry?.knowledge_level || 0);
    if (nextLevel > prevLevel) addNovelty(campaignId, `codex:beast:${beastId}`, Math.floor(nextLevel - prevLevel));
    if (prevLevel <= 0 && nextLevel > 0) addNovelty(campaignId, `beast:new:${beastId}`, 1);
  });
}

function clearCharacterNovelty(slotId, tabId = "overview") {
  const campaignId = CAMPAIGN?.campaign_meta?.campaign_id || SESSION?.campaignId || "";
  if (!campaignId || !slotId) return;
  const scope = String(tabId || "overview");
  const keys = scope === "skills"
    ? [`skill:${slotId}`]
    : scope === "class"
    ? [`class:${slotId}`]
    : scope === "injuries"
    ? [`injury:${slotId}`]
    : [`skill:${slotId}`, `class:${slotId}`, `injury:${slotId}`];
  let changed = false;
  keys.forEach((key) => {
    if (clearNovelty(campaignId, key)) changed = true;
  });
  if (changed) renderPartyOverview();
}

function clearCodexNovelty(kind, entityId) {
  const campaignId = CAMPAIGN?.campaign_meta?.campaign_id || SESSION?.campaignId || "";
  if (!campaignId || !kind || !entityId) return;
  const keys = kind === "beast"
    ? [`codex:beast:${entityId}`, `beast:new:${entityId}`]
    : [`codex:race:${entityId}`];
  let changed = false;
  keys.forEach((key) => {
    if (clearNovelty(campaignId, key)) changed = true;
  });
  if (changed) renderCharactersTab();
}

function saveSessionLibrary(library) {
  SESSION_LIBRARY = library;
  localStorage.setItem("isekaiSessionLibrary", JSON.stringify(library));
}

function upsertSessionLibrary(entry) {
  const next = SESSION_LIBRARY.filter((item) => item.campaignId !== entry.campaignId);
  next.unshift({ ...entry, lastUsedAt: new Date().toISOString() });
  saveSessionLibrary(next);
}

function removeSessionLibraryEntry(campaignId) {
  saveSessionLibrary(SESSION_LIBRARY.filter((item) => item.campaignId !== campaignId));
}

function libraryEntry(campaignId) {
  return SESSION_LIBRARY.find((item) => item.campaignId === campaignId) || null;
}

function loadTheme() {
  const stored = localStorage.getItem("isekaiTheme");
  return ["arcane", "tavern", "glade", "hybrid"].includes(stored) ? stored : "arcane";
}

function loadFontPreset() {
  const stored = localStorage.getItem("isekaiFontPreset");
  return ["classic", "clean", "literary"].includes(stored) ? stored : "classic";
}

function loadFontSize() {
  const stored = localStorage.getItem("isekaiFontSize");
  return ["small", "medium", "large"].includes(stored) ? stored : "medium";
}

function saveTheme(themeId) {
  localStorage.setItem("isekaiTheme", themeId);
}

function saveFontPreset(fontPreset) {
  localStorage.setItem("isekaiFontPreset", fontPreset);
}

function saveFontSize(fontSize) {
  localStorage.setItem("isekaiFontSize", fontSize);
}

function applyTheme(themeId) {
  CURRENT_THEME = VALID_THEMES.includes(themeId) ? themeId : "arcane";
  document.documentElement.dataset.theme = CURRENT_THEME;
}

function applyFontPreset(fontPreset) {
  CURRENT_FONT_PRESET = ["classic", "clean", "literary"].includes(fontPreset) ? fontPreset : "classic";
  document.documentElement.dataset.fontPreset = CURRENT_FONT_PRESET;
}

function applyFontSize(fontSize) {
  CURRENT_FONT_SIZE = ["small", "medium", "large"].includes(fontSize) ? fontSize : "medium";
  document.documentElement.dataset.fontSize = CURRENT_FONT_SIZE;
}

function setTheme(themeId) {
  applyTheme(themeId);
  saveTheme(CURRENT_THEME);
  renderBoards();
  showFlash(`Style gewechselt: ${THEME_LABELS[CURRENT_THEME] || "Style"}`);
}

function setFontPreset(fontPreset) {
  applyFontPreset(fontPreset);
  saveFontPreset(CURRENT_FONT_PRESET);
  renderBoards();
  showFlash(`Schriftart gewechselt: ${FONT_PRESET_LABELS[CURRENT_FONT_PRESET] || "Schrift"}`);
}

function setFontSize(fontSize) {
  applyFontSize(fontSize);
  saveFontSize(CURRENT_FONT_SIZE);
  renderBoards();
  showFlash(`Schriftgröße gewechselt: ${FONT_SIZE_LABELS[CURRENT_FONT_SIZE] || "Größe"}`);
}

function authHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  if (SESSION.playerId && SESSION.playerToken) {
    headers["X-Player-Id"] = SESSION.playerId;
    headers["X-Player-Token"] = SESSION.playerToken;
  }
  return headers;
}

function resetLiveState() {
  disconnectLiveEvents();
  LIVE_STATE.activitiesByPlayer = {};
  LIVE_STATE.blockingAction = null;
  LIVE_STATE.sseConnected = false;
  LIVE_STATE.version = 0;
  LIVE_STATE.campaignId = null;
  LIVE_STATE.localLoadingVisible = false;
  LIVE_STATE.localLoadingMessage = "Einen Moment bitte.";
  LIVE_STATE.reconnectNeedsReload = false;
  window.clearTimeout(LIVE_STATE.reloadTimer);
  window.clearTimeout(LIVE_STATE.typingTimer);
  window.clearTimeout(LIVE_STATE.setupTimer);
  window.clearTimeout(LIVE_STATE.editTimer);
  window.clearTimeout(LIVE_STATE.highlightTimer);
  LIVE_STATE.reloadTimer = null;
  LIVE_STATE.typingTimer = null;
  LIVE_STATE.setupTimer = null;
  LIVE_STATE.editTimer = null;
  LIVE_STATE.highlightTimer = null;
  LIVE_STATE.highlightTurnId = null;
  LAST_STORY_SCROLL_CAMPAIGN_ID = null;
  renderLoadingOverlay();
}

function showFlash(message, isError = false) {
  const flash = el("flash");
  flash.textContent = message;
  flash.style.borderColor = isError ? "rgba(255,150,150,.28)" : "rgba(173,195,240,.18)";
  flash.classList.remove("hidden");
  window.clearTimeout(showFlash.timer);
  showFlash.timer = window.setTimeout(() => flash.classList.add("hidden"), 3500);
}

function switchView(viewId) {
  ["landing-view", "claim-view", "campaign-view"].forEach((id) => {
    el(id).classList.toggle("hidden", id !== viewId);
  });
}

function loadingMessageFor(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  if (path.includes("/intro/retry")) {
    return "Der Kampagnenauftakt wird erneut aufgebaut...";
  }
  if (path.includes("/turns")) {
    return method === "PATCH" ? "Turn wird überarbeitet..." : "Der GM denkt gerade nach...";
  }
  if (path.includes("/setup/world")) {
    if (path.includes("/random")) return "Der GM erzeugt gerade einen Weltvorschlag...";
    return "Die Welt wird gerade definiert...";
  }
  if (path.includes("/slots/") && path.includes("/setup/")) {
    if (path.includes("/random")) return "Der GM erzeugt gerade einen Figurenvorschlag...";
    return "Die Figur wird gerade ausgearbeitet...";
  }
  if (path.includes("/slots/") && path.includes("/claim")) {
    return "Slot wird geclaimt...";
  }
  if (path.includes("/api/campaigns/join")) {
    return "Trete der Session bei...";
  }
  if (path === "/api/campaigns") {
    return "Kampagne wird erstellt...";
  }
  if (path.includes("/export")) {
    return "Session wird exportiert...";
  }
  if (path.includes("/boards/")) {
    return "Board wird gespeichert...";
  }
  if (path.includes("/api/campaigns/")) {
    return "Session wird geladen...";
  }
  return "Einen Moment bitte...";
}

function showLoading(message) {
  LIVE_STATE.localLoadingVisible = true;
  LIVE_STATE.localLoadingMessage = message;
  renderLoadingOverlay();
}

function hideLoading() {
  LIVE_STATE.localLoadingVisible = false;
  renderLoadingOverlay();
}

function renderLoadingOverlay() {
  const sharedMessage = LIVE_STATE.blockingAction?.label || "";
  const localMessage = LIVE_STATE.localLoadingVisible ? LIVE_STATE.localLoadingMessage : "";
  const message = sharedMessage || localMessage;
  if (!message) {
    el("loading-overlay").classList.add("hidden");
    return;
  }
  el("loading-text").textContent = message;
  el("loading-overlay").classList.remove("hidden");
}

function isSharedBlocking() {
  return Boolean(LIVE_STATE.blockingAction);
}

function beginLoading(message) {
  PENDING_REQUESTS += 1;
  LIVE_STATE.localLoadingMessage = message;
  if (PENDING_REQUESTS === 1) {
    window.clearTimeout(LOADING_TIMER);
    LOADING_TIMER = window.setTimeout(() => showLoading(message), 180);
  } else if (LIVE_STATE.localLoadingVisible) {
    renderLoadingOverlay();
  }
}

function endLoading() {
  PENDING_REQUESTS = Math.max(0, PENDING_REQUESTS - 1);
  if (PENDING_REQUESTS === 0) {
    window.clearTimeout(LOADING_TIMER);
    LOADING_TIMER = null;
    hideLoading();
  }
}

async function api(path, options = {}) {
  const headers = authHeaders(options.headers || {});
  beginLoading(loadingMessageFor(path, options));
  try {
    const response = await fetch(path, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      let message = data.detail || "Unbekannter Fehler";
      if (Array.isArray(message)) {
        message = message.map((entry) => entry.msg || JSON.stringify(entry)).join(" | ");
      }
      if (typeof message === "object") {
        message = JSON.stringify(message);
      }
      throw new Error(message);
    }
    return data;
  } finally {
    endLoading();
  }
}

async function backgroundApi(path, options = {}) {
  const headers = authHeaders(options.headers || {});
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = data.detail || "Unbekannter Fehler";
    if (Array.isArray(message)) {
      message = message.map((entry) => entry.msg || JSON.stringify(entry)).join(" | ");
    }
    if (typeof message === "object") {
      message = JSON.stringify(message);
    }
    throw new Error(message);
  }
  return data;
}

function setBusy(buttonId, busy, busyText = "...", idleText = null) {
  const button = el(buttonId);
  if (!button) return;
  button.disabled = busy;
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.textContent = busyText;
  } else if (idleText) {
    button.textContent = idleText;
  } else if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
  }
}

function viewer() {
  return CAMPAIGN?.viewer_context || {};
}

function isHost() {
  return Boolean(viewer().is_host);
}

function claimedSlotId() {
  return viewer().claimed_slot_id || null;
}

function claimedSlot() {
  const slotId = claimedSlotId();
  return (CAMPAIGN?.available_slots || []).find((slot) => slot.slot_id === slotId) || null;
}

function currentPlayer() {
  return viewer().player_id || SESSION.playerId || null;
}

function applyLiveSnapshot(live) {
  LIVE_STATE.activitiesByPlayer = { ...(live?.activities || {}) };
  LIVE_STATE.blockingAction = live?.blocking_action || null;
  LIVE_STATE.version = Number(live?.version || LIVE_STATE.version || 0);
  renderLoadingOverlay();
  renderLiveDecorations();
}

function buildEventsUrl() {
  const params = new URLSearchParams({
    player_id: SESSION.playerId || "",
    player_token: SESSION.playerToken || ""
  });
  return `/api/campaigns/${SESSION.campaignId}/events?${params.toString()}`;
}

function disconnectLiveEvents() {
  if (LIVE_STATE.eventSource) {
    LIVE_STATE.eventSource.close();
    LIVE_STATE.eventSource = null;
  }
  LIVE_STATE.sseConnected = false;
}

function scheduleCampaignReload() {
  if (LIVE_STATE.reloadTimer) return;
  LIVE_STATE.reloadTimer = window.setTimeout(async () => {
    LIVE_STATE.reloadTimer = null;
    if (!SESSION.campaignId || !SESSION.playerId || !SESSION.playerToken) return;
    await loadCampaign({ silent: true });
  }, 80);
}

function connectLiveEvents() {
  if (!SESSION.campaignId || !SESSION.playerId || !SESSION.playerToken) return;
  if (LIVE_STATE.eventSource && LIVE_STATE.campaignId === SESSION.campaignId) return;
  disconnectLiveEvents();
  LIVE_STATE.campaignId = SESSION.campaignId;
  const source = new EventSource(buildEventsUrl());
  LIVE_STATE.eventSource = source;
  source.addEventListener("open", () => {
    const shouldReload = LIVE_STATE.reconnectNeedsReload;
    LIVE_STATE.sseConnected = true;
    LIVE_STATE.reconnectNeedsReload = false;
    if (shouldReload) scheduleCampaignReload();
    renderLiveDecorations();
  });
  source.addEventListener("campaign_sync", (event) => {
    const payload = JSON.parse(event.data || "{}");
    LIVE_STATE.version = Math.max(LIVE_STATE.version, Number(payload.version || 0));
    scheduleCampaignReload();
  });
  source.addEventListener("presence_sync", (event) => {
    const payload = JSON.parse(event.data || "{}");
    applyLiveSnapshot(payload);
  });
  source.addEventListener("ping", () => {});
  source.onerror = () => {
    LIVE_STATE.sseConnected = false;
    LIVE_STATE.reconnectNeedsReload = true;
    renderLiveDecorations();
  };
}

async function sendPresenceActivity(kind, extra = {}) {
  if (!SESSION.campaignId || !SESSION.playerId || !SESSION.playerToken) return;
  try {
    const data = await backgroundApi(`/api/campaigns/${SESSION.campaignId}/presence/activity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, ...extra })
    });
    if (data.live) applyLiveSnapshot(data.live);
  } catch {}
}

async function clearPresenceActivity() {
  if (!SESSION.campaignId || !SESSION.playerId || !SESSION.playerToken) return;
  try {
    const data = await backgroundApi(`/api/campaigns/${SESSION.campaignId}/presence/clear`, { method: "POST" });
    if (data.live) applyLiveSnapshot(data.live);
  } catch {}
}

function scheduleTypingPresence() {
  window.clearTimeout(LIVE_STATE.typingTimer);
  LIVE_STATE.typingTimer = window.setTimeout(() => {
    const value = el("turn-input")?.value?.trim();
    if (!value || !claimedSlotId()) {
      clearPresenceActivity();
      return;
    }
    sendPresenceActivity("typing_turn", { slot_id: claimedSlotId() });
  }, 220);
}

function scheduleSetupPresence() {
  window.clearTimeout(LIVE_STATE.setupTimer);
  LIVE_STATE.setupTimer = window.setTimeout(() => {
    if (!SETUP_FLOW.mode) return;
    const kind = SETUP_FLOW.mode === "world" ? "building_world" : "building_character";
    const payload = SETUP_FLOW.mode === "world" ? {} : { slot_id: SETUP_FLOW.slotId || claimedSlotId() };
    sendPresenceActivity(kind, payload);
  }, 220);
}

function scheduleEditPresence(turnId = EDIT_TURN_ID) {
  window.clearTimeout(LIVE_STATE.editTimer);
  LIVE_STATE.editTimer = window.setTimeout(() => {
    if (!turnId) return;
    sendPresenceActivity("editing_turn", { target_turn_id: turnId });
  }, 220);
}

function formatDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("de-DE");
  } catch {
    return value;
  }
}

function playerDisplayName(playerId) {
  return (CAMPAIGN?.players || []).find((player) => player.player_id === playerId)?.display_name || "Jemand";
}

function cardActivity(card) {
  if (!card?.claimed_by) return null;
  return LIVE_STATE.activitiesByPlayer[card.claimed_by] || null;
}

function primaryLiveActivity() {
  const ownId = currentPlayer();
  const ownActivity = ownId ? LIVE_STATE.activitiesByPlayer[ownId] : null;
  if (ownActivity) return ownActivity;
  const entries = Object.values(LIVE_STATE.activitiesByPlayer || {});
  entries.sort((left, right) => new Date(right.updated_at || 0) - new Date(left.updated_at || 0));
  return entries[0] || null;
}

function renderActivityBar() {
  const bar = el("live-activity-bar");
  if (!bar) return;
  const blocking = LIVE_STATE.blockingAction;
  const active = blocking || primaryLiveActivity();
  if (!active) {
    bar.classList.add("hidden");
    bar.innerHTML = "";
    return;
  }
  const status = blocking ? "Gemeinsame Aktion" : "Live";
  bar.className = `live-activity-bar live-activity-chip${blocking ? " blocking" : ""}`;
  bar.innerHTML = `
    <div class="live-activity-icon" aria-hidden="true"></div>
    <div class="live-activity-copy">
      <strong>${escapeHtml(status)}</strong>
      <span>${escapeHtml(active.label || "Jemand ist aktiv...")}</span>
    </div>
    <div class="live-activity-state">${LIVE_STATE.sseConnected ? "Verbunden" : "Verbindung wird erneuert..."}</div>
  `;
}

function syncSharedBlockingControls() {
  const sharedBlocking = isSharedBlocking();
  const claimed = claimedSlot();
  const isAdventure = CAMPAIGN?.state?.meta?.phase === "adventure";
  const hasIntro = campaignHasIntro();
  const intro = introState();

  const unclaimBtn = el("unclaimBtn");
  if (unclaimBtn) unclaimBtn.disabled = !claimed || sharedBlocking;

  const turnInput = el("turn-input");
  if (turnInput) turnInput.disabled = !claimed || !isAdventure || !hasIntro || sharedBlocking;

  const submitTurnBtn = el("submitTurnBtn");
  if (submitTurnBtn) submitTurnBtn.disabled = !claimed || !isAdventure || !hasIntro || sharedBlocking;

  const composerHint = el("composer-hint");
  if (composerHint) {
    composerHint.textContent = sharedBlocking
      ? "Während gerade ein Zug oder Setup verarbeitet wird, kannst du weiterlesen und dich umsehen, aber nichts Neues absenden."
      : !isAdventure
      ? "Vor dem Abenteuer müssen Welt und alle benötigten Figuren abgeschlossen sein."
      : !hasIntro && intro.status === "failed"
      ? "Der Auftakt muss zuerst erfolgreich erzeugt werden, bevor du neue Beiträge senden kannst."
      : !hasIntro
      ? "Der GM bereitet gerade noch den ersten Szenenauftakt vor."
      : claimed
      ? CURRENT_ACTION_TYPE === "canon"
        ? "Dieser Beitrag wird direkt als kanonischer Zustand übernommen und ab dem nächsten Turn als Wahrheit behandelt."
        : `Der GM baut deinen ${actionTypeLabel(CURRENT_ACTION_TYPE)}-Beitrag direkt in die laufende Szene ein.`
      : "Ohne Claim kannst du lesen, aber keinen Turn senden.";
  }

  document.querySelectorAll('[data-action="edit-turn"], [data-action="undo-turn"], [data-action="retry-turn"], [data-action="continue-turn"], [data-action="claim-slot"], [data-action="take-slot"]').forEach((node) => {
    node.disabled = sharedBlocking;
  });

  const setupIds = ["setupPrevBtn", "setupSkipBtn", "setupSubmitBtn", "setupRandomBtn", "setupRandomRerollBtn", "setupRandomApplyBtn"];
  setupIds.forEach((id) => {
    const node = el(id);
    if (node) node.disabled = sharedBlocking;
  });
  ["setup-question-root", "setup-other-root"].forEach((id) => {
    const root = el(id);
    if (!root) return;
    root.querySelectorAll("input, textarea, select, button").forEach((node) => {
      node.disabled = sharedBlocking;
    });
  });

  const diaryInput = el("player-diary-input");
  if (diaryInput) diaryInput.disabled = sharedBlocking;
  const diarySaveBtn = el("savePlayerDiaryBtn");
  if (diarySaveBtn) diarySaveBtn.disabled = sharedBlocking;
  const saveEditBtn = el("saveEditBtn");
  if (saveEditBtn) saveEditBtn.disabled = sharedBlocking;
  const retryIntroBtn = el("retryIntroBtn");
  if (retryIntroBtn) retryIntroBtn.disabled = sharedBlocking;
}

function renderLiveDecorations() {
  renderLoadingOverlay();
  renderActivityBar();
  syncSharedBlockingControls();
  if (CAMPAIGN && !el("claim-view").classList.contains("hidden")) renderClaimView();
  if (CAMPAIGN && !el("campaign-view").classList.contains("hidden")) renderPartyOverview();
}

function titleizeToken(value) {
  const lowered = (value || "").toString().toLowerCase();
  const map = {
    str: "Stärke (STR)",
    dex: "Geschicklichkeit (DEX)",
    con: "Konstitution (CON)",
    int: "Intelligenz (INT)",
    wis: "Weisheit (WIS)",
    cha: "Charisma (CHA)",
    luck: "Glück (LUCK)",
    hp: "HP",
    stamina: "Ausdauer",
    aether: "Ressource",
    stress: "Stress",
    corruption: "Verderbnis",
    physical: "Physisch",
    fire: "Feuer",
    cold: "Kälte",
    lightning: "Blitz",
    poison: "Gift",
    bleed: "Blutung",
    shadow: "Schatten",
    holy: "Heilig",
    curse: "Fluch",
    fear: "Furcht",
    weapon: "Waffe",
    offhand: "Nebenhand",
    head: "Kopf",
    chest: "Brust",
    gloves: "Handschuhe",
    boots: "Stiefel",
    amulet: "Amulett",
    ring_1: "Ring 1",
    ring_2: "Ring 2",
    trinket: "Talisman",
    stealth: "Heimlichkeit",
    perception: "Wahrnehmung",
    survival: "Überleben",
    athletics: "Athletik",
    intimidation: "Einschüchtern",
    persuasion: "Überzeugen",
    lore_occult: "Okkultes Wissen",
    crafting: "Handwerk",
    lockpicking: "Schlösser knacken",
    endurance: "Ausdauer",
    willpower: "Willenskraft",
    tactics: "Taktik"
  };
  if (map[lowered]) return map[lowered];
  return (value || "")
    .toString()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function ageStageLabel(value) {
  return AGE_STAGE_LABELS[String(value || "").toLowerCase()] || value || "-";
}

function buildLabel(value) {
  return BUILD_LABELS[String(value || "").toLowerCase()] || value || "-";
}

function auraLabel(value) {
  return AURA_LABELS[String(value || "").toLowerCase()] || value || "-";
}

function encumbranceLabel(value) {
  return ENCUMBRANCE_LABELS[String(value || "").toLowerCase()] || value || "-";
}

function appearanceEventLabel(value) {
  return APPEARANCE_EVENT_LABELS[String(value || "").toLowerCase()] || value || "Veränderung";
}

function phaseLabel(phase) {
  return {
    world_setup: "Welt-Setup",
    character_setup: "Charakter-Setup",
    adventure: "Abenteuer"
  }[phase] || phase || "-";
}

function renderSessionLibrary() {
  const root = el("session-library-list");
  if (!SESSION_LIBRARY.length) {
    root.innerHTML = `<div class="empty-library">Noch keine gespeicherten Sessions. Erstelle eine neue Kampagne oder tritt einer bestehenden bei.</div>`;
    return;
  }
  root.innerHTML = SESSION_LIBRARY.map((entry) => `
    <article class="session-card">
      <div class="session-card-main">
        <div class="session-card-title">${escapeHtml(entry.title || "Unbenannte Session")}</div>
        <div class="session-card-meta">
          <span class="badge">${escapeHtml(entry.joinCode || "kein Code")}</span>
          <span class="badge">${escapeHtml(entry.displayName || "Spieler")}</span>
          ${entry.claimedLabel ? `<span class="badge">${escapeHtml(entry.claimedLabel)}</span>` : ""}
          ${entry.isHost ? `<span class="badge">Host</span>` : ""}
        </div>
        <div class="small">Zuletzt genutzt: ${formatDate(entry.lastUsedAt)} • Session-ID: ${escapeHtml(entry.campaignId)}</div>
      </div>
      <div class="session-card-actions">
        <button class="btn primary" data-action="open-session" data-campaign-id="${entry.campaignId}" type="button">Öffnen</button>
        <button class="btn ghost" data-action="edit-session" data-campaign-id="${entry.campaignId}" type="button">Editor</button>
        <button class="btn ghost" data-action="forget-session" data-campaign-id="${entry.campaignId}" type="button">Aus Liste</button>
      </div>
    </article>
  `).join("");
}

function contributionLabel(turn) {
  return turn.actor_display || turn.actor || "Spieler";
}

function actionTypeLabel(actionType) {
  return {
    do: "TUN",
    say: "SAGEN",
    story: "STORY",
    canon: "CANON",
    context: "KONTEXT"
  }[actionType] || actionType || "";
}

function introState() {
  return CAMPAIGN?.state?.meta?.intro_state || { status: "idle", last_error: "", generated_turn_id: "" };
}

function campaignHasIntro() {
  return Boolean((CAMPAIGN?.active_turns || []).length);
}

function contributionText(turn) {
  const text = (turn.input_text_display || "").trim();
  if (!text) return "";
  if (turn.action_type === "say") return `"${text}"`;
  return text;
}

function normalizedTurnText(value) {
  return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
}

function storyResponseMarkup(turn) {
  const gmText = String(turn.gm_text_display || "").trim();
  const playerText = String(turn.input_text_display || "").trim();
  if (turn.action_type !== "story" || !playerText) {
    return escapeHtml(gmText);
  }
  const normalizedGm = normalizedTurnText(gmText);
  const normalizedPlayer = normalizedTurnText(playerText);
  if (!normalizedPlayer) return escapeHtml(gmText);
  const playerIsAlreadyInGm = normalizedGm.startsWith(normalizedPlayer) || normalizedGm.includes(normalizedPlayer.slice(0, Math.min(36, normalizedPlayer.length)));
  if (playerIsAlreadyInGm) {
    return escapeHtml(gmText);
  }
  return `<span class="story-inline-impulse">${escapeHtml(playerText)}</span>${gmText ? ` ${escapeHtml(gmText)}` : ""}`;
}

function isContinueDisplayTurn(turn) {
  return turn?.action_type === "story" && !String(turn?.input_text_display || "").trim();
}

function buildDisplayTurns(turns) {
  const displayTurns = [];
  for (const rawTurn of turns || []) {
    const turn = { ...rawTurn };
    if (isContinueDisplayTurn(turn) && displayTurns.length) {
      const previous = displayTurns[displayTurns.length - 1];
      const previousText = String(previous.gm_text_display || "").trim();
      const continueText = String(turn.gm_text_display || "").trim();
      previous.gm_text_display = [previousText, continueText].filter(Boolean).join("\n\n");
      previous.turn_id = turn.turn_id;
      previous.status = turn.status;
      previous.updated_at = turn.updated_at;
      previous.edited_at = turn.edited_at;
      previous.edit_count = turn.edit_count;
      previous.can_edit = turn.can_edit;
      previous.can_undo = turn.can_undo;
      previous.can_retry = turn.can_retry;
      previous.patch_summary = turn.patch_summary;
      previous.requests = turn.requests;
      previous.retry_of_turn_id = turn.retry_of_turn_id;
      previous.merged_continue = true;
      previous.merged_turn_count = (previous.merged_turn_count || 1) + 1;
      continue;
    }
    displayTurns.push({ ...turn, merged_continue: false, merged_turn_count: 1 });
  }
  return displayTurns;
}

function setRecentTurnHighlight(turnId) {
  window.clearTimeout(LIVE_STATE.highlightTimer);
  LIVE_STATE.highlightTurnId = turnId || null;
  LIVE_STATE.highlightTimer = null;
}

function clearRecentTurnHighlight(turnId = null) {
  if (!LIVE_STATE.highlightTurnId) return;
  if (turnId && LIVE_STATE.highlightTurnId !== turnId) return;
  LIVE_STATE.highlightTurnId = null;
  LIVE_STATE.highlightTimer = null;
  if (CAMPAIGN && !el("campaign-view").classList.contains("hidden")) {
    renderTurns();
  }
}

function scheduleStoryScrollLatest() {
  window.requestAnimationFrame(() => {
    const turns = el("turns");
    if (turns) turns.scrollTop = turns.scrollHeight;
  });
}

function renderTurns() {
  const root = el("turns");
  const turns = CAMPAIGN?.active_turns || [];
  const displayTurns = buildDisplayTurns(turns);
  if (!displayTurns.length) {
    const intro = introState();
    const message = CAMPAIGN?.state?.meta?.phase === "adventure"
      ? intro.status === "failed"
        ? "Der Auftakt fehlt noch. Versuche ihn erneut, bevor neue Beiträge gesendet werden."
        : "Die Geschichte wartet auf den ersten GM-Auftakt."
      : "Sobald Welt und Figuren fertig sind, eröffnet der GM die erste Szene.";
    root.innerHTML = `<div class="empty-state small">${message}</div>`;
    return;
  }
  const latestTurnId = displayTurns[displayTurns.length - 1]?.turn_id;
  const sharedBlocking = isSharedBlocking();
  const highlightTurnId = LIVE_STATE.highlightTurnId;
  root.innerHTML = displayTurns.map((turn) => `
    <article class="turn-card">
      <div class="story-meta">
        <span>${formatDate(turn.created_at)}</span>
        ${turn.edit_count ? `<span>${turn.edit_count} Edit${turn.edit_count > 1 ? "s" : ""}</span>` : ""}
      </div>
      ${contributionText(turn) && turn.action_type !== "story" ? `
        <div class="story-input">
          <div class="story-input-labels">
            <span class="story-speaker">${escapeHtml(contributionLabel(turn))}</span>
            <span class="type-badge type-${escapeHtml(turn.action_type)}">${escapeHtml(actionTypeLabel(turn.action_type))}</span>
          </div>
          <div class="story-input-text">${escapeHtml(contributionText(turn))}</div>
        </div>
      ` : ""}
      <div class="story-response ${turn.turn_id === highlightTurnId ? "turn-highlight" : ""}" data-turn-id="${turn.turn_id}">
        ${storyResponseMarkup(turn)}
      </div>
      <div class="turn-actions">
        ${(turn.turn_id === latestTurnId && turn.can_edit) ? `<button class="btn ghost" data-action="edit-turn" data-turn-id="${turn.turn_id}" type="button" ${sharedBlocking ? "disabled" : ""}>Bearbeiten</button>` : ""}
        ${(turn.turn_id === latestTurnId && turn.can_undo) ? `<button class="btn ghost" data-action="undo-turn" data-turn-id="${turn.turn_id}" type="button" ${sharedBlocking ? "disabled" : ""}>Zurücknehmen</button>` : ""}
        ${(turn.turn_id === latestTurnId && turn.can_retry) ? `<button class="btn ghost" data-action="retry-turn" data-turn-id="${turn.turn_id}" type="button" ${sharedBlocking ? "disabled" : ""}>Erneut versuchen</button>` : ""}
        ${(turn.turn_id === latestTurnId && claimedSlotId()) ? `<button class="btn primary" data-action="continue-turn" type="button" ${sharedBlocking ? "disabled" : ""}>Weiter</button>` : ""}
      </div>
    </article>
  `).join("");
}

function renderIntroBanner() {
  const banner = el("intro-banner");
  const title = el("intro-banner-title");
  const text = el("intro-banner-text");
  const button = el("retryIntroBtn");
  const intro = introState();
  const isAdventure = CAMPAIGN?.state?.meta?.phase === "adventure";
  const hasIntro = campaignHasIntro();
  if (!isAdventure || hasIntro) {
    banner.classList.add("hidden");
    button.classList.add("hidden");
    return;
  }
  banner.classList.remove("hidden");
  if (intro.status === "failed") {
    title.textContent = "Auftakt fehlgeschlagen";
    text.textContent = intro.last_error
      ? `Der Kampagnenauftakt konnte gerade nicht erzeugt werden. ${intro.last_error}`
      : "Der Kampagnenauftakt konnte gerade nicht erzeugt werden.";
    button.classList.toggle("hidden", !isHost());
  } else {
    title.textContent = "Auftakt wird vorbereitet";
    text.textContent = "Die Figuren sind fertig. Der GM muss noch den ersten Szenenauftakt erzeugen.";
    button.classList.add("hidden");
  }
}

function renderClaimView() {
  const meta = CAMPAIGN.campaign_meta;
  el("claim-campaign-title").textContent = meta.title;
  const requiredPlayers = CAMPAIGN.setup?.world?.summary?.player_count || 0;
  const finishedCharacters = Object.values(CAMPAIGN.setup?.characters || {}).filter((entry) => entry.completed).length;
  el("claim-meta").textContent = `Sitzung ${meta.campaign_id} • ${CAMPAIGN.players.length} Spieler • Figuren ${finishedCharacters}/${requiredPlayers || "-"}`;

  const mine = claimedSlotId();
  const root = el("claim-cards");
  root.innerHTML = (CAMPAIGN.available_slots || []).map((slot) => {
    const mineSlot = mine === slot.slot_id;
    const locked = slot.claimed_by && !mineSlot;
    const canTakeOver = !mineSlot && Boolean(slot.claimed_by || mine);
    const buttonDisabled = isSharedBlocking();
    const activity = slot.claimed_by ? LIVE_STATE.activitiesByPlayer[slot.claimed_by] : null;
    const status = slot.claimed_by ? (mineSlot ? "Du" : `Von ${slot.claimed_by_name || "jemandem"} gespielt`) : "Frei";
    const label = slot.completed ? slot.display_name : `Slot ${slot.slot_id.split("_")[1]}`;
    const summary = slot.completed
      ? `${slot.class_name || "Noch ohne Klasse"}${slot.class_rank ? ` (${slot.class_rank})` : ""} • ${slot.summary.current_focus || "Ohne Fokus"}`
      : "Noch keine fertige Figur in diesem Slot.";
    return `
      <div class="claim-card ${locked ? "locked" : ""} ${mineSlot ? "is-self" : ""}">
        <div>
          <div class="turn-actor">${escapeHtml(label)}</div>
          <div class="status-pill">${escapeHtml(status)}${slot.completed ? " • erstellt" : ""}</div>
        </div>
        <div class="small claim-card-meta-line">${escapeHtml(slot.slot_id.toUpperCase())}${slot.claimed_by_name ? ` • ${escapeHtml(slot.claimed_by_name)}` : ""}</div>
        <div class="small">${escapeHtml(summary)}</div>
        <div class="claim-activity ${activity ? "" : "is-idle"}">${escapeHtml(activity?.label || (slot.claimed_by ? "Gerade ruhig." : "Wartet auf einen Spieler."))}</div>
        <button class="btn ${(mineSlot || canTakeOver) ? "primary" : "ghost"}" data-action="${canTakeOver ? "take-slot" : "claim-slot"}" data-slot-id="${slot.slot_id}" type="button" ${buttonDisabled ? "disabled" : ""}>
          ${mineSlot ? "Slot übernehmen" : canTakeOver ? "Slot übernehmen" : "Slot claimen"}
        </button>
      </div>
    `;
  }).join("");
}

function renderPartyOverview() {
  const root = el("party-overview");
  const cards = CAMPAIGN?.party_overview || [];
  const campaignId = CAMPAIGN?.campaign_meta?.campaign_id || "";
  if (!cards.length) {
    root.innerHTML = `<div class="empty-state small">Noch keine Party-Slots sichtbar.</div>`;
    return;
  }
  const claimBadge = (card) => {
    if (card.slot_id === claimedSlotId()) return "DU";
    if (card.claimed_by_name) return String(card.claimed_by_name).toUpperCase();
    return "FREI";
  };
  const nextSnapshot = {};
  root.innerHTML = cards.map((card) => `
    <div class="party-card ${card.slot_id === claimedSlotId() ? "is-self" : ""}" data-action="open-character-sheet" data-slot-id="${card.slot_id}" role="button" tabindex="0">
      <div class="party-card-head">
        <div>
          <div class="party-card-name">${escapeHtml(card.display_name || card.slot_id)} ${noveltyMarkerMarkup(campaignId, `skill:${card.slot_id}`, true)}</div>
          <div class="small party-card-subline">Ort: ${escapeHtml(card.scene_name || "???")}</div>
        </div>
        <span class="badge">${escapeHtml(claimBadge(card))}</span>
      </div>
      <div class="party-card-classline">
        <span class="party-class-badge">${escapeHtml(card.class_name || "Keine Klasse")} ${card.class_rank ? `(${escapeHtml(card.class_rank)})` : ""}</span>${noveltyMarkerMarkup(campaignId, `class:${card.slot_id}`, true)}
        ${card.class_level ? `<span class="small">Lv ${card.class_level}/${card.class_level_max || 10}</span>` : `<span class="small">Noch keine Klasse</span>`}
      </div>
      <div class="party-activity ${cardActivity(card) ? "" : "is-idle"}">${escapeHtml(cardActivity(card)?.label || (card.claimed_by ? "Gerade ruhig." : "Wartet auf einen Spieler."))}</div>
      <div class="party-hud-bars">
        ${partyHudBarMarkup("HP", card.hp_current, card.hp_max, "hp", PARTY_HUD_PREV[`${card.slot_id}:hp`] ?? card.hp_pct)}
        ${partyHudBarMarkup("STA", card.sta_current, card.sta_max, "sta", PARTY_HUD_PREV[`${card.slot_id}:sta`] ?? card.sta_pct)}
        ${partyHudBarMarkup(card.resource_name || "Ressource", card.res_current, card.res_max, "res", PARTY_HUD_PREV[`${card.slot_id}:res`] ?? card.res_pct)}
      </div>
      <div class="party-chip-row">
        <button class="mini-pill clickable-pill" data-action="open-character-sheet" data-slot-id="${card.slot_id}" data-open-tab="injuries" type="button">INJ ${card.injury_count ?? 0} ${noveltyLabel(campaignId, `injury:${card.slot_id}`)}</button>
        <button class="mini-pill clickable-pill" data-action="open-character-sheet" data-slot-id="${card.slot_id}" data-open-tab="injuries" type="button">SCAR ${card.scar_count ?? 0}</button>
        <span class="mini-pill">CARRY ${card.carry_current ?? 0}/${card.carry_max ?? 0}</span>
      </div>
      <div class="small">${escapeHtml(card.age ? `${card.age} • ${ageStageLabel(card.age_stage)}` : ageStageLabel(card.age_stage))}</div>
      <div class="small">${escapeHtml(card.appearance_short || "Unauffällig")}</div>
      <div class="condition-pills">
        ${(card.conditions || []).slice(0, 3).map((condition) => `<span class="mini-pill">${escapeHtml(condition)}</span>`).join("")}
        ${card.in_combat ? `<span class="mini-pill">Im Kampf</span>` : ""}
      </div>
    </div>
  `).join("");
  for (const card of cards) {
    nextSnapshot[`${card.slot_id}:hp`] = Number(card.hp_pct ?? 0);
    nextSnapshot[`${card.slot_id}:sta`] = Number(card.sta_pct ?? 0);
    nextSnapshot[`${card.slot_id}:res`] = Number(card.res_pct ?? 0);
  }
  animatePartyHudBars(root);
  PARTY_HUD_PREV = nextSnapshot;
}

function partyHudBarMarkup(label, current, max, tone, previousPct = null) {
  const safeMax = Math.max(Number(max || 0), 1);
  const safeCurrent = Math.max(0, Number(current || 0));
  const width = Math.max(0, Math.min(100, Math.round((safeCurrent / safeMax) * 100)));
  const startWidth = previousPct == null ? width : Math.max(0, Math.min(100, Math.round(Number(previousPct || 0))));
  const deltaClass = width < startWidth ? "delta-down" : width > startWidth ? "delta-up" : "";
  return `
    <div class="hud-bar ${tone} ${deltaClass}">
      <div class="hud-bar-top"><span>${escapeHtml(label)}</span><span>${width}%</span></div>
      <div class="hud-bar-track"><div class="hud-bar-fill" style="width:${startWidth}%" data-target-width="${width}"></div></div>
    </div>
  `;
}

function animatePartyHudBars(root) {
  if (!root) return;
  const bars = root.querySelectorAll(".hud-bar-fill[data-target-width]");
  if (!bars.length) return;
  requestAnimationFrame(() => {
    bars.forEach((bar) => {
      const target = Number(bar.dataset.targetWidth || 0);
      bar.style.width = `${Math.max(0, Math.min(100, target))}%`;
      bar.removeAttribute("data-target-width");
    });
  });
}

function currentDrawerTabs() {
  if (DRAWER_MODE === "npc") return NPC_DRAWER_TABS;
  if (DRAWER_MODE === "codex") return CODEX_DRAWER_TABS;
  return PC_DRAWER_TABS;
}

function applyDrawerTabLayout(mode) {
  DRAWER_MODE = mode === "npc" ? "npc" : mode === "codex" ? "codex" : "pc";
  const configs = currentDrawerTabs();
  const buttons = Array.from(document.querySelectorAll(".drawer-tab"));
  buttons.forEach((button, index) => {
    const config = configs[index];
    if (!config) {
      button.classList.add("hidden");
      button.classList.remove("active");
      return;
    }
    button.classList.remove("hidden");
    button.dataset.drawerTab = config.id;
    button.textContent = config.label;
  });
}

function setDrawerTab(tabId) {
  const available = currentDrawerTabs();
  const allowedIds = available.map((entry) => entry.id);
  if (!allowedIds.includes(tabId)) {
    tabId = available[0]?.id || "overview";
  }
  ACTIVE_DRAWER_TAB = tabId;
  document.querySelectorAll(".drawer-tab").forEach((button) => {
    const isVisible = allowedIds.includes(button.dataset.drawerTab);
    if (!isVisible) return;
    button.classList.toggle("active", button.dataset.drawerTab === tabId);
  });
  DRAWER_PANEL_IDS.forEach((id) => {
    const panel = el(`drawer-panel-${id}`);
    if (!panel) return;
    panel.classList.toggle("hidden", id !== tabId || !allowedIds.includes(id));
  });
}

function detailRow(label, value) {
  const safeValue = value === undefined || value === null || value === "" ? "-" : String(value);
  return `<div class="small"><strong>${escapeHtml(label)}:</strong> ${escapeHtml(safeValue)}</div>`;
}

function normalizeNpcFieldText(value) {
  return String(value || "").trim();
}

function isNpcStatusOnlyLabel(value) {
  const normalized = normalizeNpcFieldText(value)
    .toLowerCase()
    .replace(/\s+/g, " ");
  return (
    normalized === "active"
    || normalized === "status active"
    || normalized === "status: active"
    || normalized === "status : active"
    || normalized === "status=active"
  );
}

function npcRoleHintLabel(value) {
  const hint = normalizeNpcFieldText(value);
  if (!hint || isNpcStatusOnlyLabel(hint)) return "Unklar";
  return hint;
}

function isNpcStatusHistoryLine(value) {
  const normalized = normalizeNpcFieldText(value).toLowerCase();
  if (!normalized) return false;
  return /^status\s*[:=]/.test(normalized) || normalized === "active";
}

function skillRankClass(rank) {
  return `rank-${String(rank || "F").toLowerCase()}`;
}

function meterMarkup(label, current, max) {
  const cappedMax = Math.max(Number(max || 0), 1);
  const numericCurrent = Math.max(Number(current || 0), 0);
  const width = Math.max(0, Math.min(100, Math.round((numericCurrent / cappedMax) * 100)));
  return `
    <div class="meter">
      <div class="meter-label"><span>${escapeHtml(label)}</span><span>${numericCurrent}/${cappedMax}</span></div>
      <div class="meter-track"><div class="meter-fill" style="width:${width}%"></div></div>
    </div>
  `;
}

function abilityTypeLabel(type) {
  const normalized = String(type || "active").toLowerCase();
  if (normalized === "passive") return "Passiv";
  if (normalized === "utility") return "Utility";
  if (normalized === "ultimate") return "Ultimativ";
  return "Aktiv";
}

function formatAbilityCost(cost) {
  const entries = Object.entries(cost || {}).filter(([, value]) => Number(value || 0) > 0);
  if (!entries.length) return "-";
  return entries.map(([key, value]) => `${titleizeToken(key)} ${value}`).join(" • ");
}

function formatAbilityScaling(scaling) {
  const entries = Object.entries(scaling || {}).filter(([, value]) => value);
  if (!entries.length) return "-";
  return entries.map(([key, value]) => `${titleizeToken(key)}: ${value}`).join(" • ");
}

function formatAbilityRequirements(requirements) {
  const list = (requirements || []).map((entry) => {
    if (typeof entry === "string") return entry;
    if (!entry || typeof entry !== "object") return "";
    return Object.entries(entry)
      .filter(([, value]) => value !== undefined && value !== null && value !== "")
      .map(([key, value]) => `${titleizeToken(key)}: ${value}`)
      .join(", ");
  }).filter(Boolean);
  return list.length ? list.join(" • ") : "-";
}

const ATTRIBUTE_CHART_ORDER = ["str", "dex", "con", "int", "wis", "cha", "luck"];

function attributeScaleMeta(stats) {
  const scale = stats?.attribute_scale || {};
  const min = Math.max(0, Number(scale.min || 1));
  const max = Math.max(1, Number(scale.max || 10));
  return {
    label: scale.label || `${min || 1}-${max}`,
    min,
    max
  };
}

function polarPoint(cx, cy, radius, angleRadians) {
  return {
    x: cx + Math.cos(angleRadians) * radius,
    y: cy + Math.sin(angleRadians) * radius
  };
}

function pointsToSvg(points) {
  return points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
}

function attributeRadarSvgMarkup(attributes, scaleMeta, size = 420) {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.28;
  const labelRadius = radius + 44;
  const svgStyle = `
    .attribute-radar-grid{fill:none;stroke:rgba(255,255,255,.1);stroke-width:1}
    .attribute-radar-axis{stroke:rgba(255,255,255,.12);stroke-width:1}
    .attribute-radar-area{fill:url(#attributeRadarFill);stroke:rgba(244,194,108,.9);stroke-width:2}
    .attribute-radar-dot{fill:#f4c26c;stroke:rgba(12,18,28,.9);stroke-width:1.5}
    .attribute-radar-core{fill:rgba(255,255,255,.82)}
    .attribute-radar-label{fill:#f4eee4;font-size:11px;letter-spacing:.02em;font-family:Georgia,"Times New Roman",serif}
    .attribute-radar-label tspan:last-child{fill:rgba(244,238,228,.7);font-size:10px}
    .attribute-radar-tick{fill:rgba(244,238,228,.64);font-size:10px;font-family:"Trebuchet MS","Segoe UI",Tahoma,sans-serif}
  `;
  const entries = ATTRIBUTE_CHART_ORDER.map((key, index) => {
    const angle = (-Math.PI / 2) + ((Math.PI * 2 * index) / ATTRIBUTE_CHART_ORDER.length);
    const rawValue = Number(attributes?.[key] ?? 0);
    const clamped = Math.max(0, Math.min(scaleMeta.max, rawValue));
    return {
      key,
      label: titleizeToken(key),
      value: rawValue,
      clamped,
      angle
    };
  });
  const gridLevels = 5;
  const gridPolygons = Array.from({ length: gridLevels }, (_, levelIndex) => {
    const level = (levelIndex + 1) / gridLevels;
    const points = entries.map((entry) => polarPoint(cx, cy, radius * level, entry.angle));
    return `<polygon class="attribute-radar-grid" points="${pointsToSvg(points)}"></polygon>`;
  }).join("");
  const axes = entries.map((entry) => {
    const end = polarPoint(cx, cy, radius, entry.angle);
    return `<line class="attribute-radar-axis" x1="${cx}" y1="${cy}" x2="${end.x.toFixed(2)}" y2="${end.y.toFixed(2)}"></line>`;
  }).join("");
  const labels = entries.map((entry) => {
    const point = polarPoint(cx, cy, labelRadius, entry.angle);
    const anchor = Math.abs(point.x - cx) < 10 ? "middle" : (point.x > cx ? "start" : "end");
    return `<text class="attribute-radar-label" x="${point.x.toFixed(2)}" y="${point.y.toFixed(2)}" text-anchor="${anchor}">
      <tspan x="${point.x.toFixed(2)}" dy="0">${escapeHtml(entry.label)}</tspan>
      <tspan x="${point.x.toFixed(2)}" dy="14">${entry.clamped}/${scaleMeta.max}</tspan>
    </text>`;
  }).join("");
  const areaPoints = entries.map((entry) => polarPoint(cx, cy, radius * (entry.clamped / Math.max(scaleMeta.max, 1)), entry.angle));
  const dataArea = `<polygon class="attribute-radar-area" points="${pointsToSvg(areaPoints)}"></polygon>`;
  const valueDots = areaPoints.map((point) => `<circle class="attribute-radar-dot" cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="4"></circle>`).join("");
  const tickLabels = Array.from({ length: gridLevels }, (_, levelIndex) => {
    const value = Math.round((scaleMeta.max / gridLevels) * (levelIndex + 1));
    const y = cy - (radius * ((levelIndex + 1) / gridLevels));
    return `<text class="attribute-radar-tick" x="${cx + 10}" y="${y.toFixed(2)}">${value}</text>`;
  }).join("");
  return `
    <svg class="attribute-radar-svg" xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="Attributprofil als Septagon">
      <style>${svgStyle}</style>
      <defs>
        <linearGradient id="attributeRadarFill" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#f4c26c" stop-opacity="0.58"></stop>
          <stop offset="100%" stop-color="#81b1ff" stop-opacity="0.18"></stop>
        </linearGradient>
      </defs>
      ${gridPolygons}
      ${axes}
      <circle class="attribute-radar-core" cx="${cx}" cy="${cy}" r="4"></circle>
      ${tickLabels}
      ${dataArea}
      ${valueDots}
      ${labels}
    </svg>
  `;
}

function bestSkillSummary(skills, limit = 3) {
  return (skills || [])
    .slice()
    .sort((left, right) => {
      const rightPower = Number(right.effective_bonus ?? right.level ?? 0);
      const leftPower = Number(left.effective_bonus ?? left.level ?? 0);
      if (rightPower !== leftPower) return rightPower - leftPower;
      const rightMastery = Number(right.mastery ?? 0);
      const leftMastery = Number(left.mastery ?? 0);
      return rightMastery - leftMastery;
    })
    .slice(0, limit)
    .map((skill) => skill.name || titleizeToken(skill.id || ""))
    .filter(Boolean);
}

function buildAttributeExportSvgMarkup(characterSheet) {
  const stats = characterSheet?.sheet?.stats || {};
  const overview = characterSheet?.sheet?.overview || {};
  const metaInfo = characterSheet?.sheet?.meta || {};
  const skills = characterSheet?.sheet?.skills || [];
  const scaleMeta = attributeScaleMeta(stats);
  const width = 900;
  const height = 720;
  const chartSize = 600;
  const chartMarkup = attributeRadarSvgMarkup(stats.attributes || {}, scaleMeta, chartSize)
    .replace(
      '<svg class="attribute-radar-svg" xmlns="http://www.w3.org/2000/svg"',
      `<svg class="attribute-radar-svg" xmlns="http://www.w3.org/2000/svg" x="240" y="60"`
    );
  const classText = sheet.class?.current?.name || overview.class_current?.name || "Keine Klasse";
  const topSkills = bestSkillSummary(skills).join(", ") || "-";
  const infoLines = [
    { label: "Name", value: characterSheet.display_name || characterSheet.slot_id || "-" },
    { label: "Klasse", value: classText },
    { label: "Top-Skills", value: topSkills }
  ];
  const infoRows = infoLines.map((entry, index) => `
    <text class="attribute-export-copy" x="36" y="${102 + (index * 76)}">
      <tspan class="attribute-export-label" x="36" dy="0">${escapeHtml(entry.label)}</tspan>
      <tspan class="attribute-export-value" x="36" dy="22">${escapeHtml(entry.value)}</tspan>
    </text>
  `).join("");
  return `<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="Attributprofil mit Charakterinfos">
      <defs>
        <linearGradient id="attributeExportBg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#0f1a28"></stop>
          <stop offset="100%" stop-color="#09111a"></stop>
        </linearGradient>
      </defs>
      <style>
        .attribute-export-panel{fill:rgba(255,255,255,0.04);stroke:rgba(244,194,108,0.24);stroke-width:1.2}
        .attribute-export-kicker{fill:rgba(244,238,228,0.72);font-size:11px;letter-spacing:.22em;text-transform:uppercase;font-family:"Trebuchet MS","Segoe UI",Tahoma,sans-serif}
        .attribute-export-copy{font-family:Georgia,"Times New Roman",serif}
        .attribute-export-label{fill:rgba(244,238,228,0.72);font-size:11px;letter-spacing:.12em;text-transform:uppercase}
        .attribute-export-value{fill:#f4eee4;font-size:18px}
      </style>
      <rect x="0" y="0" width="${width}" height="${height}" fill="url(#attributeExportBg)"></rect>
      <rect class="attribute-export-panel" x="24" y="24" rx="24" ry="24" width="236" height="336"></rect>
      <text class="attribute-export-kicker" x="36" y="52">Charakterprofil</text>
      ${infoRows}
      ${chartMarkup}
    </svg>`;
}

async function exportAttributeChartPng() {
  if (!CHARACTER_SHEET) return;
  let svgUrl = "";
  try {
    const svgMarkup = buildAttributeExportSvgMarkup(CHARACTER_SHEET);
    const svgBlob = new Blob([svgMarkup], { type: "image/svg+xml;charset=utf-8" });
    svgUrl = URL.createObjectURL(svgBlob);
    const image = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Chart konnte nicht gerendert werden."));
      img.src = svgUrl;
    });
    const canvas = document.createElement("canvas");
    canvas.width = 900;
    canvas.height = 720;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas-Kontext konnte nicht erzeugt werden.");
    ctx.fillStyle = "#0d1621";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    const pngBlob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!pngBlob) throw new Error("PNG-Export fehlgeschlagen.");
    const url = URL.createObjectURL(pngBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(CHARACTER_SHEET.display_name || CHARACTER_SHEET.slot_id || "attribute_chart").replace(/[^\w\-]+/g, "_")}_werte.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showFlash("Attributgrafik als PNG exportiert.");
  } catch (error) {
    showFlash(error.message || "PNG-Export fehlgeschlagen.", true);
  } finally {
    if (svgUrl) URL.revokeObjectURL(svgUrl);
  }
}

function formatSkillCost(cost) {
  if (!cost || !cost.resource) return "-";
  return `${cost.resource} ${cost.amount ?? 0}`;
}

function skillTagSummary(skill) {
  return (skill.tags || []).slice(0, 4).join(", ");
}

function renderCharacterDrawer() {
  if (!CHARACTER_SHEET) return;
  NPC_SHEET = null;
  CODEX_SHEET = null;
  applyDrawerTabLayout("pc");
  const sheet = CHARACTER_SHEET.sheet || {};
  const overview = sheet.overview || {};
  const stats = sheet.stats || {};
  const progression = sheet.progression || {};
  const appearance = overview.appearance || {};
  const ageing = overview.ageing || {};
  const metaInfo = sheet.meta || {};
  const classInfo = sheet.class || {};
  const currentClass = classInfo.current || overview.class_current || null;
  const injuriesScars = sheet.injuries_scars || {};
  const resourceLabel = overview.resource_label || progression.resource_name || CAMPAIGN?.state?.world?.settings?.resource_name || "Ressource";
  el("drawer-title").textContent = CHARACTER_SHEET.display_name || CHARACTER_SHEET.slot_id;
  el("drawer-subtitle").textContent = `${CHARACTER_SHEET.scene_name || "Kein Ort"} • ${CHARACTER_SHEET.claimed_by_name || "Nicht geclaimt"}`;

  el("drawer-panel-overview").innerHTML = `
    <details class="accordion" open>
      <summary>Übersicht</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Name", overview.bio?.name)}
          ${detailRow("Geschlecht", overview.bio?.gender)}
          ${detailRow("Alter", `${overview.bio?.age_years ?? "-"} • ${ageStageLabel(overview.bio?.age_stage)}`)}
          ${detailRow("Klasse", currentClass?.name ? `${currentClass.name} (${currentClass.rank || "F"})` : "Noch keine Klasse")}
          ${detailRow("Ziel", overview.bio?.goal)}
          ${detailRow("Isekai-Preis", overview.bio?.isekai_price)}
        </div>
        <div class="sheet-block">
          ${detailRow("Ort", overview.location?.scene_name)}
          ${detailRow("Leben auf der Erde", overview.bio?.earth_life)}
          ${detailRow("Persönlichkeit", (overview.bio?.personality || []).join(", "))}
          ${detailRow("Tags", (overview.bio?.background_tags || []).join(", "))}
        </div>
      </div>
    </details>
    <details class="accordion" open>
      <summary>Aussehen</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Kurzbeschreibung", appearance.summary_short)}
          ${detailRow("Größe", appearance.height)}
          ${detailRow("Körperbau", buildLabel(appearance.build))}
          ${detailRow("Muskelgrad", appearance.muscle)}
          ${detailRow("Aura", auraLabel(appearance.aura))}
          ${detailRow("Stimme", appearance.voice_tone)}
        </div>
        <div class="sheet-block">
          ${detailRow("Augen", appearance.eyes?.current || appearance.eyes?.base)}
          ${detailRow("Haare", appearance.hair?.current)}
          ${detailRow("Hautzeichen", (appearance.skin_marks || []).join(", "))}
          ${detailRow("Narben", (appearance.scars || []).map((entry) => entry.label).join(", "))}
          ${detailRow("Visuelle Marker", (appearance.visual_modifiers || []).map((entry) => entry.value).join(", "))}
        </div>
      </div>
    </details>
    <details class="accordion" open>
      <summary>Altern</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Alter in Jahren", overview.bio?.age_years)}
          ${detailRow("Altersstufe", ageStageLabel(overview.bio?.age_stage))}
          ${detailRow("Seit Ankunft", `${ageing.days_since_arrival ?? 0} Tage`)}
          ${detailRow("Ankunft an Tag", ageing.arrival_absolute_day)}
        </div>
        <div class="sheet-block">
          ${detailRow("Letzte Alterung", ageing.last_aged_absolute_day)}
          ${detailRow("Alterungsmarker", (ageing.age_effects_applied || []).join(", "))}
        </div>
      </div>
    </details>
    <details class="accordion" open>
      <summary>Ressourcen</summary>
      <div class="accordion-body stat-grid">
        <div class="stat-card"><strong>HP</strong><div>${overview.resources?.hp?.current ?? 0}/${overview.resources?.hp?.max ?? 0}</div></div>
        <div class="stat-card"><strong>STA</strong><div>${overview.resources?.stamina?.current ?? 0}/${overview.resources?.stamina?.max ?? 0}</div></div>
        <div class="stat-card"><strong>${escapeHtml(resourceLabel)}</strong><div>${progression.resource_current ?? 0}/${progression.resource_max ?? 0}</div></div>
        <div class="stat-card"><strong>Traglast</strong><div>${sheet.gear_inventory?.carry_weight ?? 0}/${sheet.gear_inventory?.carry_limit ?? 0}</div></div>
        <div class="stat-card"><strong>Injuries</strong><div>${overview.injury_count ?? 0}</div></div>
        <div class="stat-card"><strong>Scars</strong><div>${overview.scar_count ?? 0}</div></div>
      </div>
    </details>
    <details class="accordion">
      <summary>Progression</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("System-Stufe", progression.system_level)}
          ${detailRow("System XP", progression.system_xp)}
          ${detailRow("Ressource", resourceLabel)}
          ${detailRow("Ressourcenpool", `${progression.resource_current ?? 0}/${progression.resource_max ?? 0}`)}
        </div>
        <div class="sheet-block">
          ${detailRow("Klasse", currentClass?.name || "Noch keine Klasse")}
          ${detailRow("Fraktionen", (metaInfo.faction_memberships || []).filter((entry) => entry.active !== false).map((entry) => entry.name || entry.faction_id).join(", "))}
          ${detailRow("Fusion möglich", sheet.skill_meta?.fusion_possible ? "Ja" : "Nein")}
        </div>
      </div>
    </details>
  `;

  el("drawer-panel-class").innerHTML = `
    <details class="accordion" open>
      <summary>Klasse</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Name", currentClass?.name || "Noch keine Klasse")}
          ${detailRow("Rank", currentClass?.rank || "-")}
          ${detailRow("Level", currentClass ? `${currentClass.level ?? 1}/${currentClass.level_max ?? 10}` : "-")}
          ${detailRow("XP", currentClass ? `${currentClass.xp ?? 0}/${currentClass.xp_next ?? 100}` : "-")}
          ${detailRow("Affinitäten", (currentClass?.affinity_tags || []).join(", "))}
        </div>
        <div class="sheet-block">
          ${detailRow("Beschreibung", currentClass?.description || "-")}
          ${detailRow("Ascension-Status", currentClass?.ascension?.status || "none")}
          ${detailRow("Ascension-Quest", classInfo.ascension_plotpoint?.title || "-")}
          ${detailRow("Requirements", (classInfo.ascension_plotpoint?.requirements || currentClass?.ascension?.requirements || []).join(", "))}
          ${detailRow("Result-Hint", currentClass?.ascension?.result_hint || "-")}
        </div>
      </div>
    </details>
  `;

  el("drawer-panel-attributes").innerHTML = `
    <details class="accordion" open>
      <summary>Attribute</summary>
      <div class="accordion-body attribute-radar-section">
        <div class="attribute-radar-head">
          <div class="small"><strong>Wertebereich:</strong> ${escapeHtml(attributeScaleMeta(stats).label)}</div>
          <button class="btn ghost" id="exportAttributeChartBtn" type="button">Als PNG exportieren</button>
        </div>
        <div class="attribute-radar-wrap">
          ${attributeRadarSvgMarkup(stats.attributes || {}, attributeScaleMeta(stats))}
        </div>
        <div class="stat-grid">
          ${ATTRIBUTE_CHART_ORDER.map((key) => `<div class="stat-card"><strong>${escapeHtml(titleizeToken(key))}</strong><div>${stats.attributes?.[key] ?? 0}</div></div>`).join("")}
        </div>
      </div>
    </details>
  `;

  el("drawer-panel-skills").innerHTML = `
    <details class="accordion" open>
      <summary>Skills</summary>
      <div class="accordion-body skill-list">
        ${(sheet.skills || []).length ? (sheet.skills || []).map((skill) => `
          <details class="skill-card">
            <summary>
              <div class="skill-card-head">
                <div>
                  <strong>${escapeHtml(skill.name || titleizeToken(skill.id))}</strong>
                  <div class="small">Stufe ${skill.level ?? 1}/${skill.level_max ?? 10} • ${escapeHtml(skillTagSummary(skill) || "ohne Tags")}</div>
                </div>
                <div class="inline-list">
                  <span class="rank-badge ${skillRankClass(skill.rank)}">${escapeHtml(skill.rank || "F")}</span>
                  ${skill.cost ? `<span class="mini-pill">${escapeHtml(formatSkillCost(skill.cost))}</span>` : ""}
                </div>
              </div>
            </summary>
            <div class="accordion-body">
              ${meterMarkup("XP", skill.xp, skill.next_xp)}
              <div class="sheet-grid" style="margin-top:12px">
                <div class="sheet-block">
                  ${detailRow("Mastery", `${skill.mastery ?? 0}%`)}
                  ${detailRow("Freigeschaltet durch", skill.unlocked_from || "-")}
                  ${detailRow("Kosten", formatSkillCost(skill.cost))}
                  ${detailRow("Preis", skill.price || "-")}
                  ${detailRow("Class-Match", skill.class_match ? "On-Class" : "Off-Class")}
                </div>
                <div class="sheet-block">
                  ${detailRow("Cooldown", skill.cooldown_turns == null ? "-" : `${skill.cooldown_turns} Turns`)}
                  ${detailRow("Synergie", skill.synergy_notes || "-")}
                  ${detailRow("Multiplikator", skill.effective_progress_multiplier ?? 1)}
                  ${detailRow("Beschreibung", skill.description || "-")}
                </div>
              </div>
            </div>
          </details>
        `).join("") : `<div class="small">Noch keine gelernten Skills.</div>`}
        ${(sheet.skill_meta?.fusion_hints || []).length ? `<div class="readonly-note"><strong>Fusion möglich:</strong> ${(sheet.skill_meta.fusion_hints || []).map((entry) => `${entry.label} (${entry.result_rank})`).join(" • ")}</div>` : ""}
      </div>
    </details>
  `;

  el("drawer-panel-injuries").innerHTML = `
    <details class="accordion" open>
      <summary>Injuries</summary>
      <div class="accordion-body inventory-list">
        ${(injuriesScars.injuries || []).length ? (injuriesScars.injuries || []).map((injury) => `
          <div class="inventory-item">
            <strong>${escapeHtml(injury.title || injury.id)}</strong><br/>
            <span class="small">${escapeHtml(injury.severity || "-")} • ${escapeHtml(injury.healing_stage || "-")} • ${injury.will_scar ? "hinterlässt Narbe" : "ohne Narbe"}</span><br/>
            <span class="small">${escapeHtml((injury.effects || []).join(", ") || injury.notes || "-")}</span>
          </div>
        `).join("") : `<div class="small">Keine aktiven Injuries.</div>`}
      </div>
    </details>
    <details class="accordion" open>
      <summary>Scars</summary>
      <div class="accordion-body inventory-list">
        ${(injuriesScars.scars || []).length ? (injuriesScars.scars || []).map((scar) => `
          <div class="inventory-item">
            <strong>${escapeHtml(scar.title || scar.id)}</strong><br/>
            <span class="small">Turn ${scar.created_turn ?? 0}</span><br/>
            <span class="small">${escapeHtml(scar.description || "-")}</span>
          </div>
        `).join("") : `<div class="small">Noch keine Narben.</div>`}
      </div>
    </details>
  `;

  el("drawer-panel-gear").innerHTML = `
    <details class="accordion" open>
      <summary>Ausrüstung</summary>
      <div class="accordion-body equipment-grid">
        ${Object.entries(sheet.gear_inventory?.equipment || {}).map(([slot, item]) => `
          <div class="equipment-slot">
            <strong>${escapeHtml(titleizeToken(slot))}</strong><br/>
            <span class="small">${escapeHtml(item.name || "Leer")}</span>
          </div>
        `).join("")}
      </div>
    </details>
    <details class="accordion" open>
      <summary>Inventar</summary>
      <div class="accordion-body">
        <div class="small">Traglast ${sheet.gear_inventory?.carry_weight ?? 0}/${sheet.gear_inventory?.carry_limit ?? 0} • ${escapeHtml(encumbranceLabel(sheet.gear_inventory?.encumbrance_state || "normal"))}</div>
        <div class="inventory-list" style="margin-top:10px">
          ${(sheet.gear_inventory?.inventory_items || []).length ? (sheet.gear_inventory?.inventory_items || []).map((item) => `
            <div class="inventory-item">
              <strong>${escapeHtml(item.name || item.item_id)}</strong><br/>
              <span class="small">x${item.stack} • ${escapeHtml(item.rarity || "common")} • Gewicht ${item.weight ?? 0}</span>
            </div>
          `).join("") : `<div class="small">Inventar leer.</div>`}
        </div>
      </div>
    </details>
  `;

  setDrawerTab(ACTIVE_DRAWER_TAB || "overview");
  el("character-drawer").classList.remove("hidden");
}

async function openCharacterDrawer(slotId, tabId = "overview") {
  const data = await api(`/api/campaigns/${SESSION.campaignId}/characters/${slotId}`);
  CHARACTER_SHEET = data;
  NPC_SHEET = null;
  CODEX_SHEET = null;
  DRAWER_MODE = "pc";
  ACTIVE_DRAWER_TAB = tabId;
  renderCharacterDrawer();
  clearCharacterNovelty(slotId, tabId);
}

function renderNpcDrawer() {
  if (!NPC_SHEET) return;
  CHARACTER_SHEET = null;
  CODEX_SHEET = null;
  applyDrawerTabLayout("npc");
  const sceneLabel = NPC_SHEET.last_seen_scene_name || NPC_SHEET.last_seen_scene_id || "Unbekannt";
  const roleHint = npcRoleHintLabel(NPC_SHEET.role_hint);
  const historyEntries = (NPC_SHEET.history_notes || []).filter((entry) => !isNpcStatusHistoryLine(entry));
  el("drawer-title").textContent = NPC_SHEET.name || NPC_SHEET.npc_id;
  el("drawer-subtitle").textContent = `${NPC_SHEET.race || "Unbekannt"} • Lv ${Number(NPC_SHEET.level || 1)}`;

  el("drawer-panel-overview").innerHTML = `
    <details class="accordion" open>
      <summary>Profil</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Name", NPC_SHEET.name)}
          ${detailRow("Rasse", NPC_SHEET.race || "Unbekannt")}
          ${detailRow("Alter", NPC_SHEET.age || "Unbekannt")}
          ${detailRow("Level", Number(NPC_SHEET.level || 1))}
          ${detailRow("Fraktion", NPC_SHEET.faction || "Keine")}
          ${detailRow("Rollenhinweis", roleHint)}
        </div>
        <div class="sheet-block">
          ${detailRow("Erstes Auftreten", `Turn ${Number(NPC_SHEET.first_seen_turn || 0)}`)}
          ${detailRow("Letztes Auftreten", `Turn ${Number(NPC_SHEET.last_seen_turn || 0)}`)}
          ${detailRow("Zuletzt gesehen an Ort", sceneLabel)}
          ${detailRow("Erwähnungen", Number(NPC_SHEET.mention_count || 0))}
          ${detailRow("Relevanz", Number(NPC_SHEET.relevance_score || 0))}
          ${detailRow("Tags", (NPC_SHEET.tags || []).join(", ") || "-")}
        </div>
      </div>
    </details>
  `;

  el("drawer-panel-class").innerHTML = `
    <details class="accordion" open>
      <summary>Motiv & Ziel</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Primäres Ziel", NPC_SHEET.goal || "Noch unbekannt")}
          ${detailRow("Backstory", NPC_SHEET.backstory_short || "Noch keine Kurzbiografie vorhanden.")}
        </div>
      </div>
    </details>
  `;

  el("drawer-panel-attributes").innerHTML = `
    <details class="accordion" open>
      <summary>Historie</summary>
      <div class="accordion-body inventory-list">
        ${historyEntries.length
          ? historyEntries.map((entry) => `<div class="inventory-item small">${escapeHtml(entry)}</div>`).join("")
          : `<div class="small">Noch keine Verlaufseinträge.</div>`}
      </div>
    </details>
  `;

  el("drawer-panel-skills").innerHTML = `
    <details class="accordion" open>
      <summary>Bezüge</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Fraktion", NPC_SHEET.faction || "Keine")}
          ${detailRow("Rollenhinweis", roleHint)}
          ${detailRow("Zuletzt gesehen an Ort", sceneLabel)}
        </div>
      </div>
    </details>
  `;

  const injuriesPanel = el("drawer-panel-injuries");
  const gearPanel = el("drawer-panel-gear");
  if (injuriesPanel) injuriesPanel.innerHTML = "";
  if (gearPanel) gearPanel.innerHTML = "";

  setDrawerTab(ACTIVE_DRAWER_TAB || "overview");
  el("character-drawer").classList.remove("hidden");
}

async function openNpcDrawer(npcId, tabId = "overview") {
  const data = await api(`/api/campaigns/${SESSION.campaignId}/npcs/${npcId}`);
  NPC_SHEET = data;
  CHARACTER_SHEET = null;
  CODEX_SHEET = null;
  DRAWER_MODE = "npc";
  ACTIVE_DRAWER_TAB = tabId;
  renderNpcDrawer();
}

function codexProfile(kind, entityId) {
  if (!CAMPAIGN?.state?.world) return null;
  if (kind === "race") return CAMPAIGN.state.world.races?.[entityId] || null;
  if (kind === "beast") return CAMPAIGN.state.world.beast_types?.[entityId] || null;
  return null;
}

function codexEntry(kind, entityId) {
  if (!CAMPAIGN?.state?.codex) return null;
  if (kind === "race") return CAMPAIGN.state.codex.races?.[entityId] || null;
  if (kind === "beast") return CAMPAIGN.state.codex.beasts?.[entityId] || null;
  return null;
}

function renderCodexDrawer() {
  if (!CODEX_SHEET) return;
  CHARACTER_SHEET = null;
  NPC_SHEET = null;
  applyDrawerTabLayout("codex");
  const { kind, entityId, profile, entry } = CODEX_SHEET;
  const level = Number(entry?.knowledge_level || 0);
  const kindLabel = kind === "race" ? "Rasse" : "Bestie";
  const knownBlocks = Array.isArray(entry?.known_blocks) ? entry.known_blocks : [];
  const knownFacts = Array.isArray(entry?.known_facts) ? entry.known_facts : [];
  el("drawer-title").textContent = profile?.name || entityId;
  el("drawer-subtitle").textContent = `${kindLabel} • Wissen ${level}/4 • ${codexKnowledgeLabel(level)}`;

  el("drawer-panel-overview").innerHTML = `
    <details class="accordion" open>
      <summary>Übersicht</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Typ", kindLabel)}
          ${detailRow("Name", profile?.name || entityId)}
          ${detailRow("Wissensstand", `${level}/4 (${codexKnowledgeLabel(level)})`)}
          ${detailRow("Begegnungen", Number(entry?.encounter_count || 0))}
          ${detailRow("Erstkontakt", `Turn ${Number(entry?.first_seen_turn || 0)}`)}
          ${detailRow("Zuletzt aktualisiert", `Turn ${Number(entry?.last_updated_turn || 0)}`)}
        </div>
        <div class="sheet-block">
          ${detailRow("Freigeschaltete Kapitel", knownBlocks.join(", ") || "Keine")}
          ${detailRow("Fakten", knownFacts.length ? `${knownFacts.length} Einträge` : "Keine bekannten Fakten")}
          ${kind === "beast" ? detailRow("Besiegt", Number(entry?.defeated_count || 0)) : detailRow("Bekannte Individuen", (entry?.known_individuals || []).join(", ") || "-")}
        </div>
      </div>
    </details>
  `;

  if (kind === "race") {
    el("drawer-panel-class").innerHTML = `
      <details class="accordion" open>
        <summary>Identität</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Art", profile?.kind || "-")}
            ${detailRow("Seltenheit", profile?.rarity || "-")}
            ${detailRow("Spielbar", profile?.playable ? "Ja" : "Nein")}
            ${detailRow("Sozialer Ruf", profile?.social_reputation || "-")}
          </div>
          <div class="sheet-block">
            ${detailRow("Kurzbeschreibung", profile?.description_short || "-")}
            ${detailRow("Erscheinung", profile?.appearance || "-")}
          </div>
        </div>
      </details>
    `;
    el("drawer-panel-attributes").innerHTML = `
      <details class="accordion" open>
        <summary>Herkunft</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Heimat", profile?.homeland || "-")}
            ${detailRow("Kultur", profile?.culture || "-")}
          </div>
          <div class="sheet-block">
            ${detailRow("Temperament", profile?.temperament || "-")}
            ${detailRow("Beziehungen", profile?.social_reputation || "-")}
          </div>
        </div>
      </details>
    `;
    el("drawer-panel-skills").innerHTML = `
      <details class="accordion" open>
        <summary>Stärken/Schwächen</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Stärken", (profile?.strength_tags || []).join(", ") || "-")}
            ${detailRow("Schwächen", (profile?.weakness_tags || []).join(", ") || "-")}
          </div>
          <div class="sheet-block">
            ${detailRow("Klassen-Affinitäten", (profile?.class_affinities || []).join(", ") || "-")}
            ${detailRow("Skill-Affinitäten", (profile?.skill_affinities || []).join(", ") || "-")}
          </div>
        </div>
      </details>
    `;
    el("drawer-panel-injuries").innerHTML = `
      <details class="accordion" open>
        <summary>Fähigkeiten</summary>
        <div class="accordion-body">
          <div class="small"><strong>Bekannte Individuen:</strong> ${(entry?.known_individuals || []).length ? escapeHtml((entry.known_individuals || []).join(", ")) : "Noch keine."}</div>
        </div>
      </details>
    `;
    el("drawer-panel-gear").innerHTML = `
      <details class="accordion" open>
        <summary>Lore</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Merkmale", (profile?.notable_traits || []).join(", ") || "-")}
            ${detailRow("Alias", (profile?.aliases || []).join(", ") || "-")}
          </div>
          <div class="sheet-block">
            <div class="small"><strong>Bekannte Fakten:</strong></div>
            <div class="inventory-list" style="margin-top:8px">
              ${(knownFacts.length ? knownFacts : ["Noch keine bekannten Fakten."]).map((fact) => `<div class="inventory-item small">${escapeHtml(fact)}</div>`).join("")}
            </div>
          </div>
        </div>
      </details>
    `;
  } else {
    el("drawer-panel-class").innerHTML = `
      <details class="accordion" open>
        <summary>Identität</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Kategorie", profile?.category || "-")}
            ${detailRow("Gefahr", Number(profile?.danger_rating || 1))}
            ${detailRow("Erscheinung", profile?.appearance || "-")}
          </div>
          <div class="sheet-block">
            ${detailRow("Kampfstil", profile?.combat_style || "-")}
          </div>
        </div>
      </details>
    `;
    el("drawer-panel-attributes").innerHTML = `
      <details class="accordion" open>
        <summary>Herkunft</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Lebensraum", profile?.habitat || "-")}
            ${detailRow("Verhalten", profile?.behavior || "-")}
          </div>
        </div>
      </details>
    `;
    el("drawer-panel-skills").innerHTML = `
      <details class="accordion" open>
        <summary>Stärken/Schwächen</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Stärken", (profile?.strength_tags || []).join(", ") || "-")}
            ${detailRow("Schwächen", (profile?.weakness_tags || []).join(", ") || "-")}
          </div>
        </div>
      </details>
    `;
    el("drawer-panel-injuries").innerHTML = `
      <details class="accordion" open>
        <summary>Fähigkeiten</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Bekannte Fähigkeiten", (profile?.known_abilities || []).join(", ") || "-")}
            ${detailRow("Beobachtet", (entry?.observed_abilities || []).join(", ") || "-")}
          </div>
        </div>
      </details>
    `;
    el("drawer-panel-gear").innerHTML = `
      <details class="accordion" open>
        <summary>Lore</summary>
        <div class="accordion-body sheet-grid">
          <div class="sheet-block">
            ${detailRow("Loot", (profile?.loot_tags || []).join(", ") || "-")}
            ${detailRow("Lore", (profile?.lore_notes || []).join(", ") || "-")}
            ${detailRow("Alias", (profile?.aliases || []).join(", ") || "-")}
          </div>
          <div class="sheet-block">
            <div class="small"><strong>Bekannte Fakten:</strong></div>
            <div class="inventory-list" style="margin-top:8px">
              ${(knownFacts.length ? knownFacts : ["Noch keine bekannten Fakten."]).map((fact) => `<div class="inventory-item small">${escapeHtml(fact)}</div>`).join("")}
            </div>
          </div>
        </div>
      </details>
    `;
  }

  setDrawerTab(ACTIVE_DRAWER_TAB || "overview");
  el("character-drawer").classList.remove("hidden");
}

async function openCodexDrawer(kind, entityId, tabId = "overview") {
  const profile = codexProfile(kind, entityId);
  const entry = codexEntry(kind, entityId);
  if (!profile) throw new Error("Kodex-Eintrag nicht gefunden.");
  CODEX_SHEET = { kind, entityId, profile, entry: entry || {} };
  NPC_SHEET = null;
  CHARACTER_SHEET = null;
  DRAWER_MODE = "codex";
  ACTIVE_DRAWER_TAB = tabId;
  renderCodexDrawer();
  clearCodexNovelty(kind, entityId);
}

function closeCharacterDrawer() {
  CHARACTER_SHEET = null;
  NPC_SHEET = null;
  CODEX_SHEET = null;
  DRAWER_MODE = "pc";
  applyDrawerTabLayout("pc");
  el("character-drawer").classList.add("hidden");
}

function renderStyleTab() {
  const root = el("tab-style");
  root.innerHTML = `
    <div class="panelTitle">Style</div>
    <div class="section-copy small">Wähle, wie die Oberfläche in diesem Browser wirken soll. Der Stil gilt lokal und verändert keine Session-Daten.</div>
    <div class="theme-grid">
      <article class="theme-card ${CURRENT_THEME === "arcane" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Nachtblau</strong>
            <div class="small">Der aktuelle klare, kalte GM-Look.</div>
          </div>
          <span class="badge">${CURRENT_THEME === "arcane" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="theme-preview preview-arcane">
          <div class="preview-topbar">
            <span class="preview-chip">Code: AB6LXG</span>
            <span class="preview-menu"></span>
          </div>
          <div class="preview-panel">
            <div class="preview-title">Geschichtsfluss</div>
            <div class="preview-turn">
              <div class="preview-badge">Story</div>
              <div class="preview-line long"></div>
              <div class="preview-line medium"></div>
            </div>
          </div>
        </div>
        <button class="btn ${CURRENT_THEME === "arcane" ? "ghost" : "primary"}" data-action="set-theme" data-theme="arcane" type="button">
          ${CURRENT_THEME === "arcane" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
      <article class="theme-card ${CURRENT_THEME === "tavern" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Taverne</strong>
            <div class="small">Warmes Holz, Messing und Kerzenlicht statt futuristischem Blau.</div>
          </div>
          <span class="badge">${CURRENT_THEME === "tavern" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="theme-preview preview-tavern">
          <div class="preview-topbar">
            <span class="preview-chip">Schankraum</span>
            <span class="preview-menu"></span>
          </div>
          <div class="preview-panel">
            <div class="preview-title">Abend am Kamin</div>
            <div class="preview-turn">
              <div class="preview-badge warm">Tun</div>
              <div class="preview-line long"></div>
              <div class="preview-line short"></div>
            </div>
          </div>
        </div>
        <button class="btn ${CURRENT_THEME === "tavern" ? "ghost" : "primary"}" data-action="set-theme" data-theme="tavern" type="button">
          ${CURRENT_THEME === "tavern" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
      <article class="theme-card ${CURRENT_THEME === "glade" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Waldlichtung</strong>
            <div class="small">Moosgrün, Nebel und ruhige Wildnis-Atmosphäre.</div>
          </div>
          <span class="badge">${CURRENT_THEME === "glade" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="theme-preview preview-glade">
          <div class="preview-topbar">
            <span class="preview-chip">Lichtung</span>
            <span class="preview-menu"></span>
          </div>
          <div class="preview-panel">
            <div class="preview-title">Spuren im Farn</div>
            <div class="preview-turn">
              <div class="preview-badge leaf">Sagen</div>
              <div class="preview-line long"></div>
              <div class="preview-line medium"></div>
            </div>
          </div>
        </div>
        <button class="btn ${CURRENT_THEME === "glade" ? "ghost" : "primary"}" data-action="set-theme" data-theme="glade" type="button">
          ${CURRENT_THEME === "glade" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
      <article class="theme-card ${CURRENT_THEME === "hybrid" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Isekai (Hybrid)</strong>
            <div class="small">Mittelalter trifft Tech-Magie mit klarem Kontrast.</div>
          </div>
          <span class="badge">${CURRENT_THEME === "hybrid" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="theme-preview preview-hybrid">
          <div class="preview-topbar">
            <span class="preview-chip">Hybrid-Link</span>
            <span class="preview-menu"></span>
          </div>
          <div class="preview-panel">
            <div class="preview-title">Relikt-Schnittstelle</div>
            <div class="preview-turn">
              <div class="preview-badge hybrid">Tun</div>
              <div class="preview-line long"></div>
              <div class="preview-line short"></div>
            </div>
          </div>
        </div>
        <button class="btn ${CURRENT_THEME === "hybrid" ? "ghost" : "primary"}" data-action="set-theme" data-theme="hybrid" type="button">
          ${CURRENT_THEME === "hybrid" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
    </div>
    <div class="panelTitle" style="margin-top:22px">Typografie</div>
    <div class="section-copy small">Schriftart und Größe gelten nur lokal in deinem Browser. Mittel entspricht dem aktuellen Standard.</div>
    <div class="theme-grid">
      <article class="theme-card ${CURRENT_FONT_PRESET === "classic" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Standard</strong>
            <div class="small">Die bisherige klassische Serifenschrift.</div>
          </div>
          <span class="badge">${CURRENT_FONT_PRESET === "classic" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="type-preview type-preview-classic">
          <div class="type-preview-title">Die Geschichte fließt ruhig weiter.</div>
          <div class="type-preview-copy">Kaelen tastet sich durch den Regen, während im Hintergrund das Feuer nur noch glimmt.</div>
        </div>
        <button class="btn ${CURRENT_FONT_PRESET === "classic" ? "ghost" : "primary"}" data-action="set-font-preset" data-font-preset="classic" type="button">
          ${CURRENT_FONT_PRESET === "classic" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
      <article class="theme-card ${CURRENT_FONT_PRESET === "clean" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Klar</strong>
            <div class="small">Sachlicher, moderner und etwas technischer.</div>
          </div>
          <span class="badge">${CURRENT_FONT_PRESET === "clean" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="type-preview type-preview-clean">
          <div class="type-preview-title">Die Geschichte fließt ruhig weiter.</div>
          <div class="type-preview-copy">Kaelen tastet sich durch den Regen, während im Hintergrund das Feuer nur noch glimmt.</div>
        </div>
        <button class="btn ${CURRENT_FONT_PRESET === "clean" ? "ghost" : "primary"}" data-action="set-font-preset" data-font-preset="clean" type="button">
          ${CURRENT_FONT_PRESET === "clean" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
      <article class="theme-card ${CURRENT_FONT_PRESET === "literary" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Roman</strong>
            <div class="small">Etwas buchiger und weicher für längeres Lesen.</div>
          </div>
          <span class="badge">${CURRENT_FONT_PRESET === "literary" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="type-preview type-preview-literary">
          <div class="type-preview-title">Die Geschichte fließt ruhig weiter.</div>
          <div class="type-preview-copy">Kaelen tastet sich durch den Regen, während im Hintergrund das Feuer nur noch glimmt.</div>
        </div>
        <button class="btn ${CURRENT_FONT_PRESET === "literary" ? "ghost" : "primary"}" data-action="set-font-preset" data-font-preset="literary" type="button">
          ${CURRENT_FONT_PRESET === "literary" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
    </div>
    <div class="theme-grid" style="margin-top:16px">
      <article class="theme-card ${CURRENT_FONT_SIZE === "small" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Klein</strong>
            <div class="small">Mehr Inhalt auf einmal sichtbar.</div>
          </div>
          <span class="badge">${CURRENT_FONT_SIZE === "small" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="size-preview size-preview-small">
          <div class="type-preview-title">Beispielgröße Klein</div>
          <div class="type-preview-copy">Die Schatten hinter den Ruinen wirken enger, aber du siehst mehr Text gleichzeitig.</div>
        </div>
        <button class="btn ${CURRENT_FONT_SIZE === "small" ? "ghost" : "primary"}" data-action="set-font-size" data-font-size="small" type="button">
          ${CURRENT_FONT_SIZE === "small" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
      <article class="theme-card ${CURRENT_FONT_SIZE === "medium" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Mittel</strong>
            <div class="small">Das aktuelle Standardmaß.</div>
          </div>
          <span class="badge">${CURRENT_FONT_SIZE === "medium" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="size-preview size-preview-medium">
          <div class="type-preview-title">Beispielgröße Mittel</div>
          <div class="type-preview-copy">Die Schatten hinter den Ruinen wirken enger, aber du siehst mehr Text gleichzeitig.</div>
        </div>
        <button class="btn ${CURRENT_FONT_SIZE === "medium" ? "ghost" : "primary"}" data-action="set-font-size" data-font-size="medium" type="button">
          ${CURRENT_FONT_SIZE === "medium" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
      <article class="theme-card ${CURRENT_FONT_SIZE === "large" ? "active" : ""}">
        <div class="theme-card-head">
          <div>
            <strong>Groß</strong>
            <div class="small">Angenehmer zum Lesen aus Distanz.</div>
          </div>
          <span class="badge">${CURRENT_FONT_SIZE === "large" ? "aktiv" : "verfügbar"}</span>
        </div>
        <div class="size-preview size-preview-large">
          <div class="type-preview-title">Beispielgröße Groß</div>
          <div class="type-preview-copy">Die Schatten hinter den Ruinen wirken enger, aber du siehst mehr Text gleichzeitig.</div>
        </div>
        <button class="btn ${CURRENT_FONT_SIZE === "large" ? "ghost" : "primary"}" data-action="set-font-size" data-font-size="large" type="button">
          ${CURRENT_FONT_SIZE === "large" ? "Aktiv" : "Aktivieren"}
        </button>
      </article>
    </div>
  `;
}

function renderInactiveSettingsTab(tabId, title, description) {
  const root = el(`tab-${tabId}`);
  if (!root) return;
  root.innerHTML = `
    <div class="panelTitle">${escapeHtml(title)}</div>
    <div class="empty-state small">${escapeHtml(description)}</div>
  `;
}

function renderPlotTab() {
  const root = el("tab-plot");
  const board = CAMPAIGN.boards.plot_essentials;
  const loops = (board.open_loops || []).join("\n");
  const readonly = isHost() ? "" : "readonly";
  root.innerHTML = `
    <div class="panelTitle">Plot Essentials</div>
    <div class="two-col">
      <label class="field"><span>Premise</span><textarea id="plot-premise" ${readonly}>${escapeHtml(board.premise || "")}</textarea></label>
      <label class="field"><span>Aktives Ziel</span><textarea id="plot-goal" ${readonly}>${escapeHtml(board.current_goal || "")}</textarea></label>
      <label class="field"><span>Akute Gefahr</span><textarea id="plot-threat" ${readonly}>${escapeHtml(board.current_threat || "")}</textarea></label>
      <label class="field"><span>Aktive Szene</span><textarea id="plot-scene" ${readonly}>${escapeHtml(board.active_scene || "")}</textarea></label>
      <label class="field"><span>Open Loops</span><textarea id="plot-loops" ${readonly}>${escapeHtml(loops)}</textarea></label>
      <label class="field"><span>Tone</span><textarea id="plot-tone" ${readonly}>${escapeHtml(board.tone || "")}</textarea></label>
    </div>
    <div class="small">Zuletzt aktualisiert: ${formatDate(board.updated_at)}</div>
    ${isHost() ? `<button class="btn primary" id="savePlotBtn" type="button">Plot speichern</button>` : ""}
  `;
}

function renderAuthorsNoteTab() {
  const root = el("tab-note");
  const note = CAMPAIGN.boards.authors_note;
  const readonly = isHost() ? "" : "readonly";
  root.innerHTML = `
    <div class="panelTitle">Author's Note</div>
    <div class="readonly-note">Diese Note geht bei jedem Turn direkt in den Prompt.</div>
    <label class="field">
      <span>Steuertext</span>
      <textarea id="authors-note-input" ${readonly}>${escapeHtml(note.content || "")}</textarea>
    </label>
    <div class="small">Zuletzt aktualisiert: ${formatDate(note.updated_at)}</div>
    ${isHost() ? `<button class="btn primary" id="saveAuthorsNoteBtn" type="button">Author's Note speichern</button>` : ""}
  `;
}

function renderDiaryTab() {
  const root = el("tab-diary");
  const diaries = CAMPAIGN.boards.player_diaries || {};
  const currentId = currentPlayer();
  const sharedBlocking = isSharedBlocking();
  const entries = CAMPAIGN.players.map((player) => diaries[player.player_id] || {
    player_id: player.player_id,
    display_name: player.display_name,
    content: "",
    updated_at: null,
    updated_by: player.player_id
  });
  root.innerHTML = `
    <div class="panelTitle">Diary</div>
    <div class="readonly-note">Jeder Spieler hat hier sein eigenes Tagebuch. Du kannst nur deinen eigenen Eintrag bearbeiten. Zeilen, die mit <code>//</code> beginnen, bleiben nur für dich sichtbar.</div>
    <div class="diary-list">
      ${entries.map((entry) => {
        const isOwn = entry.player_id === currentId;
        return `
          <article class="diary-card ${isOwn ? "is-self" : ""}">
            <div class="entity-meta">
              <strong>${escapeHtml(entry.display_name || "Spieler")}</strong>
              <span class="badge">${isOwn ? "dein Diary" : "read only"}</span>
            </div>
            ${isOwn ? `
              <label class="field">
                <span>Notizen</span>
                <textarea id="player-diary-input" ${sharedBlocking ? "disabled" : ""}>${escapeHtml(entry.content || "")}</textarea>
              </label>
              <div class="turn-actions">
                <button class="btn primary" id="savePlayerDiaryBtn" type="button" ${sharedBlocking ? "disabled" : ""}>Diary speichern</button>
              </div>
            ` : `
              <div class="turn-block"><div class="turn-text">${escapeHtml(entry.content || "Noch keine Notizen.")}</div></div>
            `}
            <div class="small">Zuletzt aktualisiert: ${formatDate(entry.updated_at)}</div>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function renderStoryCardsTab() {
  const root = el("tab-cards");
  const cards = CAMPAIGN.boards.story_cards || [];
  const editingCard = cards.find((card) => card.card_id === EDITING_STORY_CARD_ID);
  const kinds = ["npc", "location", "faction", "item", "hook", "rule"];
  root.innerHTML = `
    <div class="panelTitle">Story-Karten</div>
    ${isHost() ? `
      <label class="field"><span>Titel</span><input id="story-card-title" type="text" value="${escapeHtml(editingCard?.title || "")}" /></label>
      <label class="field"><span>Typ</span><select id="story-card-kind">${kinds.map((kind) => `<option value="${kind}" ${(editingCard?.kind || "npc") === kind ? "selected" : ""}>${kind}</option>`).join("")}</select></label>
      <label class="field"><span>Inhalt</span><textarea id="story-card-content">${escapeHtml(editingCard?.content || "")}</textarea></label>
      <label class="field"><span>Tags (Komma-getrennt)</span><input id="story-card-tags" type="text" value="${escapeHtml((editingCard?.tags || []).join(", "))}" /></label>
      <div class="turn-actions">
        <button class="btn primary" id="saveStoryCardBtn" type="button">${editingCard ? "Story Card speichern" : "Story Card anlegen"}</button>
        ${editingCard ? `<button class="btn ghost" id="cancelStoryCardEditBtn" type="button">Edit abbrechen</button>` : ""}
      </div>
    ` : ""}
    <div>${cards.length ? cards.map((card) => `
      <div class="entity-card">
        <div class="entity-meta">
          <strong>${escapeHtml(card.title)}</strong>
          <span class="badge">${escapeHtml(card.kind)}</span>
          ${card.archived ? `<span class="badge">archiviert</span>` : ""}
        </div>
        <div class="small">${escapeHtml(card.content)}</div>
        ${(card.tags || []).length ? `<div class="inline-list">${card.tags.map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        ${isHost() ? `<div class="turn-actions"><button class="btn ghost" data-action="edit-story-card" data-card-id="${card.card_id}" type="button">Bearbeiten</button></div>` : ""}
      </div>
    `).join("") : `<div class="small">Noch keine Story-Karten.</div>`}</div>
  `;
}

function renderWorldInfoTab() {
  const root = el("tab-world");
  const entries = CAMPAIGN.boards.world_info || [];
  const editingEntry = entries.find((entry) => entry.entry_id === EDITING_WORLD_INFO_ID);
  root.innerHTML = `
    <div class="panelTitle">World Info</div>
    ${isHost() ? `
      <label class="field"><span>Titel</span><input id="world-title" type="text" value="${escapeHtml(editingEntry?.title || "")}" /></label>
      <label class="field"><span>Kategorie</span><input id="world-category" type="text" value="${escapeHtml(editingEntry?.category || "")}" /></label>
      <label class="field"><span>Inhalt</span><textarea id="world-content">${escapeHtml(editingEntry?.content || "")}</textarea></label>
      <label class="field"><span>Tags (Komma-getrennt)</span><input id="world-tags" type="text" value="${escapeHtml((editingEntry?.tags || []).join(", "))}" /></label>
      <div class="turn-actions">
        <button class="btn primary" id="saveWorldInfoBtn" type="button">${editingEntry ? "World Info speichern" : "World Info anlegen"}</button>
        ${editingEntry ? `<button class="btn ghost" id="cancelWorldInfoEditBtn" type="button">Edit abbrechen</button>` : ""}
      </div>
    ` : ""}
    <div>${entries.length ? entries.map((entry) => `
      <div class="entity-card">
        <div class="entity-meta">
          <strong>${escapeHtml(entry.title)}</strong>
          <span class="badge">${escapeHtml(entry.category)}</span>
        </div>
        <div class="small">${escapeHtml(entry.content)}</div>
        ${(entry.tags || []).length ? `<div class="inline-list">${entry.tags.map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        ${isHost() ? `<div class="turn-actions"><button class="btn ghost" data-action="edit-world-entry" data-entry-id="${entry.entry_id}" type="button">Bearbeiten</button></div>` : ""}
      </div>
    `).join("") : `<div class="small">Noch keine World-Info-Einträge.</div>`}</div>
  `;
}

function renderMemoryTab() {
  const root = el("tab-memory");
  const board = CAMPAIGN.boards.memory_summary;
  root.innerHTML = `
    <div class="panelTitle">Memory Summary</div>
    <div class="readonly-note">Read-only. Diese Zusammenfassung wird automatisch aus den aktiven Turns gebaut.</div>
    <div class="turn-block"><div class="turn-text">${escapeHtml(board.content || "Noch keine Zusammenfassung vorhanden.")}</div></div>
    <div class="small">Aktualisiert bis Turn ${board.updated_through_turn} • ${formatDate(board.updated_at)}</div>
  `;
}

function renderSessionSettingsTab() {
  const root = el("tab-session");
  if (!CAMPAIGN) {
    root.innerHTML = `<div class="empty-state small">Keine aktive Session geladen.</div>`;
    return;
  }
  const readonly = isHost() ? "" : "readonly";
  root.innerHTML = `
    <div class="panelTitle">Session</div>
    <label class="field">
      <span>Session-Name</span>
      <input id="settings-session-title" type="text" value="${escapeHtml(CAMPAIGN.campaign_meta.title || "")}" ${readonly} />
    </label>
    <div class="readonly-note">
      <strong>Session-ID:</strong> ${escapeHtml(CAMPAIGN.campaign_meta.campaign_id)}<br/>
      <strong>Join-Code:</strong> ${escapeHtml(SESSION.joinCode || "gespeichert")}<br/>
      <strong>Status:</strong> ${isHost() ? "Host" : "Teilnehmer"}<br/>
      <strong>Aktualisiert:</strong> ${formatDate(CAMPAIGN.campaign_meta.updated_at)}
    </div>
    <div class="turn-actions">
      ${isHost() ? `<button class="btn primary" id="saveSettingsSessionBtn" type="button">Name speichern</button>` : ""}
      <button class="btn ghost" id="exportSettingsSessionBtn" type="button">Exportieren</button>
      ${isHost() ? `<button class="btn ghost" id="deleteSettingsSessionBtn" type="button">Löschen</button>` : ""}
    </div>
  `;
}

function sceneNameFromCampaign(sceneId) {
  const id = String(sceneId || "").trim();
  if (!id) return "";
  const scene = CAMPAIGN?.state?.scenes?.[id];
  if (scene?.name) return scene.name;
  const mapNode = CAMPAIGN?.state?.map?.nodes?.[id];
  if (mapNode?.name) return mapNode.name;
  return id;
}

function codexKnowledgeLabel(level) {
  const value = Number(level || 0);
  if (value <= 0) return "Unbekannt";
  if (value === 1) return "Gesichtet";
  if (value === 2) return "Beobachtet";
  if (value === 3) return "Erforscht";
  return "Vollständig";
}

function codexProgressPercent(level) {
  const value = Number(level || 0);
  return Math.max(0, Math.min(100, Math.round((value / 4) * 100)));
}

function renderCodexBlocks(knownBlocks, blockOrder) {
  const known = new Set((Array.isArray(knownBlocks) ? knownBlocks : []).map((value) => String(value || "")));
  return (blockOrder || []).map((block) => {
    const unlocked = known.has(block);
    return `<span class="codex-block-chip ${unlocked ? "is-known" : "is-locked"}">${escapeHtml(block)}</span>`;
  }).join("");
}

function setActiveCodexTab(tabId) {
  const allowed = ["npcs", "races", "beasts"];
  ACTIVE_CODEX_TAB = allowed.includes(tabId) ? tabId : "npcs";
  renderCharactersTab();
}

function renderCharactersTab() {
  const root = el("tab-chars");
  const campaignId = CAMPAIGN?.campaign_meta?.campaign_id || "";
  const npcCodex = CAMPAIGN?.state?.npc_codex || {};
  const worldRaces = CAMPAIGN?.state?.world?.races || {};
  const worldBeasts = CAMPAIGN?.state?.world?.beast_types || {};
  const codexState = CAMPAIGN?.state?.codex || {};
  const codexRaces = codexState?.races || {};
  const codexBeasts = codexState?.beasts || {};
  const activeTab = ["npcs", "races", "beasts"].includes(ACTIVE_CODEX_TAB) ? ACTIVE_CODEX_TAB : "npcs";
  const raceTabNovelty = noveltyCountByPrefix(campaignId, "codex:race:");
  const beastTabNovelty = noveltyCountByPrefix(campaignId, "codex:beast:") + noveltyCountByPrefix(campaignId, "beast:new:");

  const npcs = Object.values(npcCodex)
    .filter((entry) => entry && entry.npc_id && entry.name)
    .sort((a, b) => {
      const relevanceDiff = Number(b.relevance_score || 0) - Number(a.relevance_score || 0);
      if (relevanceDiff) return relevanceDiff;
      const seenDiff = Number(b.last_seen_turn || 0) - Number(a.last_seen_turn || 0);
      if (seenDiff) return seenDiff;
      return Number(b.mention_count || 0) - Number(a.mention_count || 0);
    });

  const raceRows = Object.entries(worldRaces)
    .filter(([, profile]) => profile && profile.name)
    .sort((a, b) => {
      const nameA = String(a[1]?.name || a[0]).toLowerCase();
      const nameB = String(b[1]?.name || b[0]).toLowerCase();
      if (nameA !== nameB) return nameA.localeCompare(nameB, "de");
      return String(a[0]).localeCompare(String(b[0]), "de");
    });

  const beastRows = Object.entries(worldBeasts)
    .filter(([, profile]) => profile && profile.name)
    .sort((a, b) => {
      const nameA = String(a[1]?.name || a[0]).toLowerCase();
      const nameB = String(b[1]?.name || b[0]).toLowerCase();
      if (nameA !== nameB) return nameA.localeCompare(nameB, "de");
      return String(a[0]).localeCompare(String(b[0]), "de");
    });

  let bodyHtml = "";
  if (activeTab === "npcs") {
    if (!npcs.length) {
      bodyHtml = `<div class="empty-state small">Noch keine story-relevanten Figuren erfasst.</div>`;
    } else {
      bodyHtml = `
        <div class="info-grid npc-lexicon-grid">
          ${npcs.map((npc) => `
            <div class="info-item npc-codex-card">
              <div class="entity-meta npc-codex-head">
                <strong>${escapeHtml(npc.name)}</strong>
                <span class="badge">Lv ${Number(npc.level || 1)}</span>
                <span class="badge">${escapeHtml(npc.race || "Unbekannt")}</span>
              </div>
              <div class="small"><strong>Ziel:</strong> ${escapeHtml(npc.goal || "Noch unbekannt.")}</div>
              <div class="small">Rolle: ${escapeHtml(npcRoleHintLabel(npc.role_hint))} • Fraktion: ${escapeHtml(npc.faction || "Keine")}</div>
              <div class="small">Zuletzt gesehen: Turn ${Number(npc.last_seen_turn || 0)}${npc.last_seen_scene_id ? ` • ${escapeHtml(sceneNameFromCampaign(npc.last_seen_scene_id))}` : ""}</div>
              <div class="small">Erwähnungen: ${Number(npc.mention_count || 0)} • Relevanz: ${Number(npc.relevance_score || 0)}</div>
              <div class="turn-actions"><button class="btn ghost" data-action="open-npc-sheet" data-npc-id="${npc.npc_id}" type="button">NPC-Bogen öffnen</button></div>
            </div>
          `).join("")}
        </div>
      `;
    }
  } else if (activeTab === "races") {
    if (!raceRows.length) {
      bodyHtml = `<div class="empty-state small">Noch keine Rassenprofile vorhanden.</div>`;
    } else {
      bodyHtml = `
        <div class="info-grid codex-grid">
          ${raceRows.map(([raceId, race]) => {
            const entry = codexRaces[raceId] || {};
            const level = Number(entry.knowledge_level || 0);
            return `
              <div class="info-item codex-compact-card">
                <div class="entity-meta codex-compact-head">
                  <strong>${escapeHtml(race.name || raceId)}</strong>
                  <span class="badge">Wissen ${level}/4</span>${noveltyMarkerMarkup(campaignId, `codex:race:${raceId}`, true)}
                </div>
                <div class="small codex-state-label">${escapeHtml(codexKnowledgeLabel(level).toUpperCase())}</div>
                <div class="small">Begegnungen: ${Number(entry.encounter_count || 0)} • Erstkontakt: Turn ${Number(entry.first_seen_turn || 0)}</div>
                <div class="turn-actions">
                  <button class="btn ghost" data-action="open-codex-entry" data-codex-kind="race" data-codex-id="${escapeHtml(raceId)}" type="button">Öffnen</button>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      `;
    }
  } else {
    if (!beastRows.length) {
      bodyHtml = `<div class="empty-state small">Noch keine Bestienprofile vorhanden.</div>`;
    } else {
      bodyHtml = `
        <div class="info-grid codex-grid">
          ${beastRows.map(([beastId, beast]) => {
            const entry = codexBeasts[beastId] || {};
            const level = Number(entry.knowledge_level || 0);
            return `
              <div class="info-item codex-compact-card">
                <div class="entity-meta codex-compact-head">
                  <strong>${escapeHtml(beast.name || beastId)}</strong>
                  <span class="badge">Wissen ${level}/4</span>${noveltyMarkerMarkup(campaignId, `codex:beast:${beastId}`, true)}${noveltyMarkerMarkup(campaignId, `beast:new:${beastId}`, true)}
                </div>
                <div class="small codex-state-label">${escapeHtml(codexKnowledgeLabel(level).toUpperCase())}</div>
                <div class="small">Begegnungen: ${Number(entry.encounter_count || 0)} • Erstkontakt: Turn ${Number(entry.first_seen_turn || 0)}</div>
                <div class="turn-actions">
                  <button class="btn ghost" data-action="open-codex-entry" data-codex-kind="beast" data-codex-id="${escapeHtml(beastId)}" type="button">Öffnen</button>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      `;
    }
  }

  root.innerHTML = `
    <div class="panelTitle">Kodex</div>
    <div class="codex-subtabs">
      <button class="codex-subtab ${activeTab === "npcs" ? "active" : ""}" data-codex-tab="npcs" type="button">NPCs</button>
      <button class="codex-subtab ${activeTab === "races" ? "active" : ""}" data-codex-tab="races" type="button">Rassen ${noveltyMarkerForCount(raceTabNovelty, true)}</button>
      <button class="codex-subtab ${activeTab === "beasts" ? "active" : ""}" data-codex-tab="beasts" type="button">Bestien ${noveltyMarkerForCount(beastTabNovelty, true)}</button>
    </div>
    ${bodyHtml}
  `;
}

function renderMapTab() {
  const root = el("tab-map");
  const nodes = CAMPAIGN.state.map?.nodes || {};
  const edges = CAMPAIGN.state.map?.edges || [];
  root.innerHTML = `
    <div class="panelTitle">Karte</div>
    ${Object.keys(nodes).length ? `
      <ul class="list">${Object.entries(nodes).map(([id, node]) => `<li><strong>${escapeHtml(node.name)}</strong> <span class="badge">${escapeHtml(id)}</span><div class="small">${escapeHtml(node.type)} • Gefahr ${node.danger} • ${node.discovered ? "entdeckt" : "unentdeckt"}</div></li>`).join("")}</ul>
    ` : `<div class="empty-state small">Noch keine Orte definiert. Die Karte bleibt leer, bis die Story echte Orte erzeugt.</div>`}
    <div class="panelTitle" style="margin-top:16px">Verbindungen</div>
    <ul class="list">${edges.length ? edges.map((edge) => `<li>${escapeHtml(edge.from)} -> ${escapeHtml(edge.to)} <span class="small">(${escapeHtml(edge.kind)})</span></li>`).join("") : "<li>Noch keine Verbindungen.</li>"}</ul>
  `;
}

function renderEventsTab() {
  const root = el("tab-events");
  const events = CAMPAIGN.state.events || [];
  root.innerHTML = `
    <div class="panelTitle">Events</div>
    <ul class="list">${events.length ? events.slice(-60).reverse().map((entry) => `<li>${escapeHtml(entry)}</li>`).join("") : "<li>Noch keine Events.</li>"}</ul>
  `;
}

function renderBoards() {
  renderStyleTab();
  if (!CAMPAIGN) {
    renderInactiveSettingsTab("plot", "Plot Essentials", "Lade oder erstelle zuerst eine Session, um Plot-Essentials zu bearbeiten.");
    renderInactiveSettingsTab("note", "Author's Note", "Die Author's Note wird verfügbar, sobald eine Session aktiv ist.");
    renderInactiveSettingsTab("cards", "Story-Karten", "Story-Karten stehen dir innerhalb einer aktiven Session zur Verfügung.");
    renderInactiveSettingsTab("world", "World Info", "World Info wird nach dem Laden einer Session angezeigt.");
    renderInactiveSettingsTab("memory", "Memory Summary", "Die Zusammenfassung erscheint erst, wenn eine Session aktiv ist.");
    renderSessionSettingsTab();
    return;
  }
  renderPlotTab();
  renderAuthorsNoteTab();
  renderStoryCardsTab();
  renderWorldInfoTab();
  renderMemoryTab();
  renderSessionSettingsTab();
  renderCharactersTab();
  renderMapTab();
  renderEventsTab();
}

function renderLanding() {
  renderSessionLibrary();
  switchView("landing-view");
}

function openSettingsModal(tabId = "plot") {
  renderBoards();
  setActiveSettingsTab(tabId);
  el("settings-modal").classList.remove("hidden");
}

function closeSettingsModal() {
  el("settings-modal").classList.add("hidden");
}

function closeSetupModal() {
  clearPresenceActivity();
  SETUP_FLOW = { mode: null, slotId: null, stack: [], index: -1 };
  el("setup-modal").classList.add("hidden");
  el("setup-progress").classList.add("hidden");
  el("setup-ai-copy").classList.add("hidden");
  el("setup-question-root").classList.add("hidden");
  el("setup-other-root").classList.add("hidden");
  el("setup-modal-actions").classList.add("hidden");
  el("setup-waiting").classList.add("hidden");
  el("setup-question-root").innerHTML = "";
  el("setup-other-root").innerHTML = "";
  closeSetupRandomModal();
}

function openWaitingSetupModal() {
  closeSetupModal();
  el("setup-modal-title").textContent = "Warte auf den Host";
  el("setup-modal-subtitle").textContent = "Die Session ist noch im Welt-Setup.";
  el("setup-waiting").classList.remove("hidden");
  el("setup-modal").classList.remove("hidden");
}

function buildCurrentSetupPrompt() {
  return SETUP_FLOW.stack[SETUP_FLOW.index] || null;
}

function pushSetupPrompt(promptState) {
  if (!promptState?.question) return;
  const current = buildCurrentSetupPrompt();
  if (current?.question?.question_id === promptState.question.question_id) {
    SETUP_FLOW.stack[SETUP_FLOW.index] = promptState;
    return;
  }
  SETUP_FLOW.stack = SETUP_FLOW.stack.slice(0, SETUP_FLOW.index + 1);
  SETUP_FLOW.stack.push(promptState);
  SETUP_FLOW.index = SETUP_FLOW.stack.length - 1;
}

function getSetupOptionEntries(question) {
  if (Array.isArray(question?.option_entries) && question.option_entries.length) {
    return question.option_entries;
  }
  return (question?.options || []).map((option) => ({
    value: option,
    label: option,
    description: ""
  }));
}

function renderSetupQuestionInput(question, answer) {
  if (question.type === "text") {
    return `<label class="field"><span>${escapeHtml(question.label)}</span><input id="setup-answer-text" type="text" value="${escapeHtml(typeof answer === "string" ? answer : "")}" /></label>`;
  }
  if (question.type === "textarea") {
    return `<label class="field"><span>${escapeHtml(question.label)}</span><textarea id="setup-answer-textarea">${escapeHtml(typeof answer === "string" ? answer : "")}</textarea></label>`;
  }
  if (question.type === "boolean") {
    const boolValue = answer === true || answer === "Ja" ? "ja" : answer === false || answer === "Nein" ? "nein" : "";
    return `
      <div class="field">
        <span>${escapeHtml(question.label)}</span>
        <div class="setup-choice-list">
          <label class="setup-choice"><input type="radio" name="setup-boolean" value="ja" ${boolValue === "ja" ? "checked" : ""} /><span>Ja</span></label>
          <label class="setup-choice"><input type="radio" name="setup-boolean" value="nein" ${boolValue === "nein" ? "checked" : ""} /><span>Nein</span></label>
        </div>
      </div>
    `;
  }
  if (question.type === "select") {
    const selected = answer?.selected || "";
    const optionEntries = getSetupOptionEntries(question);
    return `
      <div class="field">
        <span>${escapeHtml(question.label)}</span>
        <div class="setup-choice-list">
          ${optionEntries.map((entry) => `
            <label class="setup-choice ${selected === entry.value ? "is-selected" : ""}">
              <input class="setup-answer-select-choice" type="radio" name="setup-select-choice" value="${escapeHtml(entry.value)}" ${selected === entry.value ? "checked" : ""} />
              <span class="setup-choice-copy">
                <strong>${escapeHtml(entry.label)}</strong>
                ${entry.description ? `<small>${escapeHtml(entry.description)}</small>` : ""}
              </span>
            </label>
          `).join("")}
          ${question.allow_other ? `
            <label class="setup-choice ${selected === "Sonstiges" ? "is-selected" : ""}">
              <input class="setup-answer-select-choice" type="radio" name="setup-select-choice" value="__other__" ${selected === "Sonstiges" ? "checked" : ""} />
              <span class="setup-choice-copy">
                <strong>Eigene Antwort</strong>
                <small>${escapeHtml(question.other_hint || "Wenn nichts passt, beschreibe deine eigene Richtung.")}</small>
              </span>
            </label>
          ` : ""}
        </div>
      </div>
    `;
  }
  if (question.type === "multiselect") {
    const selected = new Set(answer?.selected || []);
    const optionEntries = getSetupOptionEntries(question);
    return `
      <div class="field">
        <span>${escapeHtml(question.label)}</span>
        <div class="setup-choice-list">
          ${optionEntries.map((entry) => `
            <label class="setup-choice ${selected.has(entry.value) ? "is-selected" : ""}">
              <input class="setup-answer-multi" type="checkbox" value="${escapeHtml(entry.value)}" ${selected.has(entry.value) ? "checked" : ""} />
              <span class="setup-choice-copy">
                <strong>${escapeHtml(entry.label)}</strong>
                ${entry.description ? `<small>${escapeHtml(entry.description)}</small>` : ""}
              </span>
            </label>
          `).join("")}
        </div>
      </div>
    `;
  }
  return `<div class="small">Unbekannter Feldtyp.</div>`;
}

function renderOtherInput(question, answer) {
  if (!question.allow_other) return "";
  if (question.type === "select") {
    return `<label class="field"><span>${escapeHtml(question.other_hint || "Eigene Antwort (nur ausfüllen, wenn du oben Eigene Antwort wählst)")}</span><input id="setup-answer-other" type="text" value="${escapeHtml(answer?.other_text || "")}" /></label>`;
  }
  if (question.type === "multiselect") {
    return `<label class="field"><span>${escapeHtml(question.other_hint || "Weitere Einträge (optional, durch Komma getrennt)")}</span><input id="setup-answer-other" type="text" value="${escapeHtml((answer?.other_values || []).join(", "))}" /></label>`;
  }
  return "";
}

function renderSetupModal() {
  const promptState = buildCurrentSetupPrompt();
  if (!promptState?.question) return;
  const question = promptState.question;
  const answer = question.existing_answer;
  el("setup-modal-title").textContent = SETUP_FLOW.mode === "world" ? "Welt definieren" : `Figur bauen: ${claimedSlot()?.display_name || claimedSlotId() || ""}`;
  el("setup-modal-subtitle").textContent = SETUP_FLOW.mode === "world"
    ? "Der GM führt den Run durch die Weltdefinition."
    : "Der GM führt dich jetzt durch den Charakterbau deines Slots.";
  el("setup-progress").classList.remove("hidden");
  el("setup-ai-copy").classList.remove("hidden");
  el("setup-question-root").classList.remove("hidden");
  el("setup-other-root").classList.toggle("hidden", !question.allow_other);
  el("setup-modal-actions").classList.remove("hidden");
  el("setup-progress").textContent = `Frage ${promptState.progress.step}/${promptState.progress.total}`;
  el("setup-ai-copy").textContent = question.ai_copy || question.label;
  el("setup-question-root").innerHTML = renderSetupQuestionInput(question, answer);
  el("setup-other-root").innerHTML = renderOtherInput(question, answer);
  el("setupSkipBtn").classList.toggle("hidden", question.required);
  el("setupRandomBtn").classList.toggle("hidden", !promptState?.question);
  el("setupPrevBtn").disabled = SETUP_FLOW.index <= 0;
  if (isSharedBlocking()) {
    el("setupPrevBtn").disabled = true;
    el("setupSkipBtn").disabled = true;
    el("setupSubmitBtn").disabled = true;
    el("setupRandomBtn").disabled = true;
    const questionInput = el("setup-question-root");
    questionInput.querySelectorAll("input, textarea, select, button").forEach((node) => {
      node.disabled = true;
    });
    const otherRoot = el("setup-other-root");
    otherRoot.querySelectorAll("input, textarea, select, button").forEach((node) => {
      node.disabled = true;
    });
  } else {
    const questionInput = el("setup-question-root");
    questionInput.querySelectorAll("input, textarea, select, button").forEach((node) => {
      node.disabled = false;
    });
    const otherRoot = el("setup-other-root");
    otherRoot.querySelectorAll("input, textarea, select, button").forEach((node) => {
      node.disabled = false;
    });
  }
  el("setupSubmitBtn").textContent = promptState.progress.step >= promptState.progress.total
    ? (SETUP_FLOW.mode === "world" ? "Run definieren" : "Figur abschließen")
    : "Antwort senden";
  el("setup-modal").classList.remove("hidden");
}

function openSetupFlow(mode, payload, slotId = null) {
  const normalizedSlotId = mode === "character" ? slotId : null;
  const sameFlow =
    SETUP_FLOW.mode === mode
    && (SETUP_FLOW.slotId || null) === (normalizedSlotId || null)
    && !el("setup-modal").classList.contains("hidden");

  if (!sameFlow) {
    closeSetupModal();
    SETUP_FLOW = { mode, slotId: normalizedSlotId, stack: [], index: -1 };
  } else {
    SETUP_FLOW.mode = mode;
    SETUP_FLOW.slotId = normalizedSlotId;
    el("setup-waiting").classList.add("hidden");
  }
  if (payload?.question) {
    pushSetupPrompt(payload);
    renderSetupModal();
    scheduleSetupPresence();
  }
}

function previousSetupStep() {
  if (SETUP_FLOW.index <= 0) return;
  SETUP_FLOW.index -= 1;
  renderSetupModal();
}

function readCurrentSetupAnswer() {
  const promptState = buildCurrentSetupPrompt();
  const question = promptState?.question;
  if (!question) return null;
  const payload = { question_id: question.question_id };
  if (question.type === "text") payload.value = el("setup-answer-text").value.trim();
  if (question.type === "textarea") payload.value = el("setup-answer-textarea").value.trim();
  if (question.type === "boolean") {
    const checked = document.querySelector('input[name="setup-boolean"]:checked');
    payload.value = checked?.value === "ja";
  }
  if (question.type === "select") {
    const value = document.querySelector('input[name="setup-select-choice"]:checked')?.value || "";
    if (value === "__other__") {
      payload.value = "";
      payload.other_text = (el("setup-answer-other")?.value || "").trim();
    } else {
      payload.value = value;
      payload.other_text = "";
    }
  }
  if (question.type === "multiselect") {
    payload.selected = Array.from(document.querySelectorAll(".setup-answer-multi:checked")).map((node) => node.value);
    payload.other_values = (el("setup-answer-other")?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
  }
  return payload;
}

function setupEndpointBase() {
  if (SETUP_FLOW.mode === "world") return `/api/campaigns/${SESSION.campaignId}/setup/world`;
  return `/api/campaigns/${SESSION.campaignId}/slots/${SETUP_FLOW.slotId}/setup`;
}

function currentSetupRandomMode() {
  return document.querySelector('input[name="setup-random-mode"]:checked')?.value || "single";
}

function renderSetupRandomPreview() {
  const root = el("setup-random-preview");
  if (!SETUP_RANDOM_STATE.previewAnswers.length) {
    root.innerHTML = `<div class="empty-state small">Noch kein Vorschlag erzeugt.</div>`;
    el("setupRandomApplyBtn").disabled = true;
    return;
  }
  root.innerHTML = `
    <div class="panelTitle">Vorschlag</div>
    <div class="random-preview-list">
      ${SETUP_RANDOM_STATE.previewAnswers.map((entry, index) => `
        <article class="random-preview-item">
          <div class="random-preview-head">
            <strong>${escapeHtml(SETUP_RANDOM_STATE.previewTexts[index]?.label || entry.question_id || "")}</strong>
            <button class="btn ghost random-inline-btn" data-action="reroll-preview-answer" data-index="${index}" type="button" aria-label="Nur diese Frage neu erzeugen">Neu</button>
          </div>
          <div class="small">${escapeHtml(SETUP_RANDOM_STATE.previewTexts[index]?.previewText || "")}</div>
        </article>
      `).join("")}
    </div>
  `;
  el("setupRandomApplyBtn").disabled = false;
}

function openSetupRandomModal() {
  const promptState = buildCurrentSetupPrompt();
  if (!promptState?.question) return;
  SETUP_RANDOM_STATE = {
    mode: "single",
    previewAnswers: [],
    previewTexts: [],
    questionId: promptState.question.question_id,
  };
  const single = document.querySelector('input[name="setup-random-mode"][value="single"]');
  const all = document.querySelector('input[name="setup-random-mode"][value="all"]');
  if (single) single.checked = true;
  if (all) all.checked = false;
  renderSetupRandomPreview();
  el("setup-random-modal").classList.remove("hidden");
  loadSetupRandomPreview("single");
}

function closeSetupRandomModal() {
  SETUP_RANDOM_STATE = { mode: "single", previewAnswers: [], previewTexts: [], questionId: null };
  el("setup-random-modal").classList.add("hidden");
}

async function loadSetupRandomPreview(mode = currentSetupRandomMode()) {
  const promptState = buildCurrentSetupPrompt();
  if (!promptState?.question) return;
  SETUP_RANDOM_STATE.mode = mode;
  SETUP_RANDOM_STATE.questionId = promptState.question.question_id;
  el("setupRandomRerollBtn").disabled = true;
  el("setupRandomApplyBtn").disabled = true;
  setBusy("setupRandomBtn", true, "...");
  try {
    clearPresenceActivity();
    const data = await api(`${setupEndpointBase()}/random`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, question_id: promptState.question.question_id })
    });
    SETUP_RANDOM_STATE.previewAnswers = (data.preview_answers || []).map((entry) => entry.answer || {});
    SETUP_RANDOM_STATE.previewTexts = (data.preview_answers || []).map((entry) => ({
      label: entry.label || entry.question_id,
      previewText: entry.preview_text || "",
    }));
    renderSetupRandomPreview();
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    el("setupRandomRerollBtn").disabled = false;
    setBusy("setupRandomBtn", false, "...", "Neu");
  }
}

async function rerollSetupPreviewAnswer(index) {
  const numericIndex = Number(index);
  if (!Number.isInteger(numericIndex) || numericIndex < 0 || numericIndex >= SETUP_RANDOM_STATE.previewAnswers.length) return;
  const targetAnswer = SETUP_RANDOM_STATE.previewAnswers[numericIndex];
  if (!targetAnswer?.question_id) return;
  const prefixAnswers = SETUP_RANDOM_STATE.previewAnswers.slice(0, numericIndex);
  try {
    const data = await api(`${setupEndpointBase()}/random`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: "single",
        question_id: targetAnswer.question_id,
        preview_answers: prefixAnswers,
      })
    });
    const replacement = data.preview_answers?.[0];
    if (!replacement?.answer) return;
    SETUP_RANDOM_STATE.previewAnswers[numericIndex] = replacement.answer;
    SETUP_RANDOM_STATE.previewTexts[numericIndex] = {
      label: replacement.label || replacement.question_id,
      previewText: replacement.preview_text || "",
    };
    renderSetupRandomPreview();
    showFlash("Diese Frage wurde neu erzeugt.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function applySetupRandomPreview() {
  const promptState = buildCurrentSetupPrompt();
  if (!promptState?.question || !SETUP_RANDOM_STATE.previewAnswers.length) return;
  el("setupRandomRerollBtn").disabled = true;
  el("setupRandomApplyBtn").disabled = true;
  try {
    clearPresenceActivity();
    const data = await api(`${setupEndpointBase()}/random/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: SETUP_RANDOM_STATE.mode,
        question_id: SETUP_RANDOM_STATE.questionId,
        preview_answers: SETUP_RANDOM_STATE.previewAnswers,
      })
    });
    closeSetupRandomModal();
    CAMPAIGN = data.campaign;
    if (data.question) {
      pushSetupPrompt({ question: data.question, progress: data.progress });
      renderSetupModal();
    } else {
      closeSetupModal();
      applyCampaign(data.campaign);
    }
    if (data.started_adventure) {
      showFlash("Der GM hat das Setup abgeschlossen. Die erste Szene beginnt.");
    } else if (data.randomized_count) {
      showFlash(
        data.randomized_count === 1
          ? "Der erzeugte Vorschlag wurde übernommen."
          : `${data.randomized_count} erzeugte Antworten wurden übernommen.`
      );
    }
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    el("setupRandomRerollBtn").disabled = false;
    el("setupRandomApplyBtn").disabled = false;
  }
}

async function submitSetupAnswer(skip = false) {
  const promptState = buildCurrentSetupPrompt();
  if (!promptState?.question) return;
  const payload = skip ? { question_id: promptState.question.question_id, value: "" } : readCurrentSetupAnswer();
  if (!payload) return;
  if (!skip && promptState.question.required) {
    const emptyText = payload.value === "" || payload.value === undefined;
    const emptySelect = Array.isArray(payload.selected) ? !payload.selected.length && !(payload.other_values || []).length : false;
    if ((promptState.question.type === "text" || promptState.question.type === "textarea" || promptState.question.type === "select") && emptyText && !payload.other_text) {
      showFlash("Bitte beantworte zuerst diese Frage.", true);
      return;
    }
    if (promptState.question.type === "multiselect" && emptySelect) {
      showFlash("Bitte beantworte zuerst diese Frage.", true);
      return;
    }
  }
  setBusy("setupSubmitBtn", true, "Speichere...");
  try {
    clearPresenceActivity();
    const data = await api(`${setupEndpointBase()}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    CAMPAIGN = data.campaign;
    if (data.question) {
      pushSetupPrompt({ question: data.question, progress: data.progress });
      renderSetupModal();
    } else {
      closeSetupModal();
      applyCampaign(data.campaign);
    }
    if (data.started_adventure) {
      showFlash("Die Figuren sind fertig. Die erste Szene beginnt.");
    }
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setBusy("setupSubmitBtn", false, "...", "Antwort senden");
  }
}

function renderCampaignView() {
  const meta = CAMPAIGN.campaign_meta;
  const state = CAMPAIGN.state;
  const claimed = claimedSlot();
  const isAdventure = state.meta.phase === "adventure";
  const hasIntro = campaignHasIntro();
  const intro = introState();
  const activeNames = (CAMPAIGN.display_party || []).map((entry) => entry.display_name);
  const worldTime = CAMPAIGN.world_time || state.meta.world_time || {};
  const worldBits = [worldTime.day ? `Tag ${worldTime.day}` : null, worldTime.time_of_day || state.world.time || null, worldTime.weather || state.world.weather || null].filter(Boolean);
  const timing = state.meta?.timing || {};
  const campaignLength = String(state.world?.settings?.campaign_length || "medium").toLowerCase();
  const pacingBits = [];
  if (campaignLength === "open") {
    pacingBits.push("Offene Kampagne");
  } else {
    if (timing.turns_target_est != null) pacingBits.push(`Ziel ${timing.turns_target_est}`);
    if (timing.turns_left_est != null) pacingBits.push(`Rest ${timing.turns_left_est}`);
  }
  if (typeof timing.cycle_ema_sec === "number" && Number.isFinite(timing.cycle_ema_sec)) {
    pacingBits.push(`Ø Zyklus ${Math.round(timing.cycle_ema_sec)}s`);
  }
  const sharedBlocking = isSharedBlocking();
  el("campaign-title").textContent = meta.title;
  el("campaign-meta").textContent = `Turn ${state.meta.turn} • ${phaseLabel(state.meta.phase)}${worldBits.length ? ` • ${worldBits.join(" • ")}` : ""}${pacingBits.length ? ` • ${pacingBits.join(" • ")}` : ""}`;
  el("join-code-chip").textContent = `Code: ${SESSION.joinCode || "gespeichert"}`;
  el("viewer-summary").textContent = `${viewer().display_name || "Spieler"} • ${isHost() ? "Host" : "Spieler"} • ${claimed?.display_name || claimed?.slot_id || "kein Claim"}${activeNames.length ? ` • Aktiv: ${activeNames.join(", ")}` : ""}`;
  el("unclaimBtn").disabled = !claimed || sharedBlocking;
  el("turn-input").disabled = !claimed || !isAdventure || !hasIntro || sharedBlocking;
  el("submitTurnBtn").disabled = !claimed || !isAdventure || !hasIntro || sharedBlocking;
  el("composer-hint").textContent = sharedBlocking
    ? "Während gerade ein Zug oder Setup verarbeitet wird, kannst du weiterlesen und dich umsehen, aber nichts Neues absenden."
    : !isAdventure
    ? "Vor dem Abenteuer müssen Welt und alle benötigten Figuren abgeschlossen sein."
    : !hasIntro && intro.status === "failed"
    ? "Der Auftakt muss zuerst erfolgreich erzeugt werden, bevor du neue Beiträge senden kannst."
    : !hasIntro
    ? "Der GM bereitet gerade noch den ersten Szenenauftakt vor."
    : claimed
    ? CURRENT_ACTION_TYPE === "canon"
      ? "Dieser Beitrag wird direkt als kanonischer Zustand übernommen und ab dem nächsten Turn als Wahrheit behandelt."
      : CURRENT_ACTION_TYPE === "context"
      ? "Diese Frage öffnet ein Kontext-Popup und verändert weder Story noch Weltzustand."
      : `Der GM baut deinen ${actionTypeLabel(CURRENT_ACTION_TYPE)}-Beitrag direkt in die laufende Szene ein.`
    : "Ohne Claim kannst du lesen, aber keinen Turn senden.";
  renderIntroBanner();
  renderTurns();
  renderPartyOverview();
  renderDiaryTab();
  renderBoards();
  renderActivityBar();
  setActiveSidebarTab(ACTIVE_SIDEBAR_TAB || "chars");
  setActionMode(CURRENT_ACTION_TYPE);
}

function applyCampaign(campaign) {
  const previousCampaignId = CAMPAIGN?.campaign_meta?.campaign_id || null;
  const previousLatestTurnId = (CAMPAIGN?.active_turns || []).slice(-1)[0]?.turn_id || null;
  const nextCampaignId = campaign?.campaign_meta?.campaign_id || null;
  const nextLatestTurnId = (campaign?.active_turns || []).slice(-1)[0]?.turn_id || null;
  trackCampaignNovelty(CAMPAIGN, campaign);
  CAMPAIGN = campaign;
  if (nextCampaignId !== previousCampaignId) {
    PARTY_HUD_PREV = {};
  }
  applyLiveSnapshot(campaign.live || {});
  if (nextLatestTurnId && nextLatestTurnId !== previousLatestTurnId) {
    setRecentTurnHighlight(nextLatestTurnId);
  }
  if (nextCampaignId && nextCampaignId !== LAST_STORY_SCROLL_CAMPAIGN_ID && nextCampaignId !== previousCampaignId) {
    LAST_STORY_SCROLL_CAMPAIGN_ID = nextCampaignId;
    scheduleStoryScrollLatest();
  }
  connectLiveEvents();
  if (CHARACTER_SHEET && !(campaign.character_sheet_slots || []).includes(CHARACTER_SHEET.slot_id)) {
    closeCharacterDrawer();
  }
  if (NPC_SHEET && !(campaign.state?.npc_codex || {})[NPC_SHEET.npc_id]) {
    closeCharacterDrawer();
  }
  if (CODEX_SHEET) {
    const codexExists = CODEX_SHEET.kind === "race"
      ? Boolean(campaign.state?.world?.races?.[CODEX_SHEET.entityId])
      : Boolean(campaign.state?.world?.beast_types?.[CODEX_SHEET.entityId]);
    if (!codexExists) closeCharacterDrawer();
  }
  upsertSessionLibrary({
    campaignId: campaign.campaign_meta.campaign_id,
    playerId: SESSION.playerId,
    playerToken: SESSION.playerToken,
    joinCode: SESSION.joinCode,
    title: campaign.campaign_meta.title,
    displayName: campaign.viewer_context.display_name,
    claimedLabel: claimedSlot()?.display_name || campaign.viewer_context.claimed_slot_id || "",
    isHost: campaign.viewer_context.is_host
  });

  if (campaign.viewer_context.needs_world_setup) {
    renderCampaignView();
    switchView("campaign-view");
    if (isHost()) {
      const next = campaign.setup_runtime?.world?.next_question;
      openSetupFlow("world", next || campaign.viewer_context.pending_setup_question);
    } else {
      openWaitingSetupModal();
    }
    return;
  }

  if (!claimedSlotId()) {
    closeSetupModal();
    renderClaimView();
    switchView("claim-view");
    return;
  }

  if (campaign.viewer_context.needs_character_setup) {
    renderClaimView();
    switchView("claim-view");
    const next = campaign.setup_runtime?.character;
    openSetupFlow("character", next || campaign.viewer_context.pending_setup_question, claimedSlotId());
    return;
  }

  closeSetupModal();
  renderCampaignView();
  switchView("campaign-view");
}

async function loadCampaign({ silent = false } = {}) {
  if (!SESSION.campaignId || !SESSION.playerId || !SESSION.playerToken) {
    resetLiveState();
    renderLanding();
    return;
  }
  try {
    const campaign = silent
      ? await backgroundApi(`/api/campaigns/${SESSION.campaignId}`)
      : await api(`/api/campaigns/${SESSION.campaignId}`);
    applyCampaign(campaign);
  } catch (error) {
    if (silent) {
      return;
    }
    clearSession();
    resetLiveState();
    CAMPAIGN = null;
    renderLanding();
    showFlash(error.message, true);
  }
}

function setActionMode(mode) {
  if (!ACTION_MODE_CONFIG[mode]) mode = "do";
  CURRENT_ACTION_TYPE = mode;
  document.querySelectorAll(".action-mode").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  el("turn-input").placeholder = ACTION_MODE_CONFIG[mode].placeholder;
  el("submitTurnBtn").textContent = mode === "context" ? "Frage stellen" : "Zug senden";
}

function setActiveSidebarTab(tabId) {
  ACTIVE_SIDEBAR_TAB = tabId;
  document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === tabId));
  SIDEBAR_TAB_IDS.forEach((id) => el(`tab-${id}`).classList.toggle("hidden", id !== tabId));
}

function setActiveSettingsTab(tabId) {
  ACTIVE_SETTINGS_TAB = tabId;
  document.querySelectorAll(".settings-tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === tabId));
  SETTINGS_TAB_IDS.forEach((id) => el(`tab-${id}`).classList.toggle("hidden", id !== tabId));
}

async function createCampaign() {
  const title = el("create-title").value.trim() || "Neue Isekai-Kampagne";
  const displayName = el("create-name").value.trim();
  if (!displayName) {
    showFlash("Bitte gib deinen Namen ein.", true);
    return;
  }
  setBusy("createCampaignBtn", true, "Erstelle...");
  try {
    const data = await api("/api/campaigns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, display_name: displayName })
    });
    saveSession({
      campaignId: data.campaign_id,
      playerId: data.player_id,
      playerToken: data.player_token,
      joinCode: data.join_code
    });
    applyCampaign(data.campaign);
    showFlash(`Kampagne erstellt. Join-Code: ${data.join_code}`);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setBusy("createCampaignBtn", false, "...", "Kampagne erstellen");
  }
}

async function joinCampaign() {
  const joinCode = el("join-code").value.trim().toUpperCase();
  const displayName = el("join-name").value.trim();
  if (!joinCode || !displayName) {
    showFlash("Bitte Join-Code und Namen eintragen.", true);
    return;
  }
  setBusy("joinCampaignBtn", true, "Trete bei...");
  try {
    const data = await api("/api/campaigns/join", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ join_code: joinCode, display_name: displayName })
    });
    saveSession({
      campaignId: data.campaign_id,
      playerId: data.player_id,
      playerToken: data.player_token,
      joinCode: data.join_code
    });
    applyCampaign(data.campaign);
    showFlash(`Kampagne ${data.campaign_summary.title} beigetreten.`);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setBusy("joinCampaignBtn", false, "...", "Beitreten");
  }
}

function openSessionModal(campaignId) {
  const entry = libraryEntry(campaignId);
  if (!entry) {
    showFlash("Session nicht in der lokalen Liste gefunden.", true);
    return;
  }
  SESSION_MODAL_ID = campaignId;
  el("session-modal-title").value = entry.title || "";
  el("session-modal-meta").textContent = `${entry.displayName || "Spieler"} • ${entry.joinCode || "kein Code"} • ${entry.isHost ? "Host" : "Teilnehmer"}`;
  el("session-modal").classList.remove("hidden");
}

function closeSessionModal() {
  SESSION_MODAL_ID = null;
  el("session-modal").classList.add("hidden");
}

async function openSavedSession(campaignId) {
  const entry = libraryEntry(campaignId);
  if (!entry) return;
  setActiveSession(entry);
  await loadCampaign();
}

function forgetSession(campaignId) {
  removeSessionLibraryEntry(campaignId);
  if (SESSION.campaignId === campaignId) clearSession();
  renderSessionLibrary();
}

async function claimSlot(slotId) {
  if (isSharedBlocking()) return;
  try {
    await sendPresenceActivity("claiming_slot", { slot_id: slotId });
    const data = await api(`/api/campaigns/${SESSION.campaignId}/slots/${slotId}/claim`, { method: "POST" });
    applyCampaign(data.campaign);
    showFlash(`${slotId.toUpperCase()} erfolgreich geclaimt.`);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    clearPresenceActivity();
  }
}

async function takeOverSlot(slotId) {
  if (isSharedBlocking()) return;
  try {
    await sendPresenceActivity("claiming_slot", { slot_id: slotId });
    const data = await api(`/api/campaigns/${SESSION.campaignId}/slots/${slotId}/takeover`, { method: "POST" });
    applyCampaign(data.campaign);
    showFlash(`${slotId.toUpperCase()} übernommen.`);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    clearPresenceActivity();
  }
}

async function unclaimCurrentSlot() {
  const slot = claimedSlotId();
  if (!slot || isSharedBlocking()) return;
  try {
    const data = await api(`/api/campaigns/${SESSION.campaignId}/slots/${slot}/unclaim`, { method: "POST" });
    applyCampaign(data.campaign);
    showFlash(`Claim für ${slot.toUpperCase()} gelöst.`);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function submitTurn() {
  if (IS_SENDING_TURN || isSharedBlocking()) return;
  const actor = claimedSlotId();
  const content = el("turn-input").value.trim();
  if (!actor || !content) return;
  if (CURRENT_ACTION_TYPE === "context") {
    await submitContextQuery(actor, content);
    return;
  }
  IS_SENDING_TURN = true;
  setBusy("submitTurnBtn", true, "Sende...");
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor, mode: actionTypeLabel(CURRENT_ACTION_TYPE), text: content })
    });
    el("turn-input").value = "";
    applyCampaign(data.campaign);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    IS_SENDING_TURN = false;
    setBusy("submitTurnBtn", false, "...", "Zug senden");
  }
}

function contextStatusLabel(status) {
  const value = String(status || "").toLowerCase();
  if (value === "found") return "Gefunden";
  if (value === "ambiguous") return "Mehrdeutig";
  if (value === "not_in_canon") return "Nicht im Kanon";
  return "Kontext";
}

function renderContextModalResult(result, fallbackAnswer) {
  if (!result || typeof result !== "object") {
    return `<div class="context-explanation">${escapeHtml(fallbackAnswer || "Keine Kontextantwort verfügbar.")}</div>`;
  }
  const status = String(result.status || "not_in_canon").toLowerCase();
  const title = String(result.title || result.target || "Kontext").trim() || "Kontext";
  const explanation = String(result.explanation || fallbackAnswer || "").trim() || "Keine Kontextantwort verfügbar.";
  const facts = Array.isArray(result.facts) ? result.facts.filter((entry) => String(entry || "").trim()) : [];
  const sources = Array.isArray(result.sources) ? result.sources.filter((entry) => entry && typeof entry === "object" && String(entry.label || "").trim()) : [];
  const suggestions = Array.isArray(result.suggestions) ? result.suggestions.filter((entry) => String(entry || "").trim()) : [];
  const statusClass =
    status === "found"
      ? "context-status-found"
      : status === "ambiguous"
        ? "context-status-ambiguous"
        : "context-status-missing";
  return `
    <div class="context-result">
      <div class="context-result-head">
        <span class="badge context-status-badge ${statusClass}">${escapeHtml(contextStatusLabel(status))}</span>
        <span class="context-result-title">${escapeHtml(title)}</span>
      </div>
      <div class="context-explanation">${escapeHtml(explanation)}</div>
      ${facts.length ? `
        <div class="context-section">
          <div class="context-section-label">Fakten</div>
          <ul class="context-list">
            ${facts.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("")}
          </ul>
        </div>
      ` : ""}
      ${sources.length ? `
        <div class="context-section">
          <div class="context-section-label">Gefunden in</div>
          <ul class="context-list">
            ${sources.map((entry) => `<li>${escapeHtml(entry.label || "")}</li>`).join("")}
          </ul>
        </div>
      ` : ""}
      ${suggestions.length ? `
        <div class="context-section">
          <div class="context-section-label">Ähnliche Begriffe</div>
          <div class="context-suggestions">${suggestions.map((entry) => `<span class="mini-pill">${escapeHtml(entry)}</span>`).join("")}</div>
        </div>
      ` : ""}
    </div>
  `;
}

function openContextModal(question, answer, result = null) {
  el("context-modal-question").textContent = question ? `Frage: ${question}` : "";
  el("context-modal-answer").innerHTML = renderContextModalResult(result, answer || "");
  el("context-modal").classList.remove("hidden");
}

function closeContextModal() {
  el("context-modal").classList.add("hidden");
  el("context-modal-question").textContent = "";
  el("context-modal-answer").innerHTML = "";
}

async function submitContextQuery(actor, content) {
  IS_SENDING_TURN = true;
  setBusy("submitTurnBtn", true, "Frage...");
  try {
    const data = await api(`/api/campaigns/${SESSION.campaignId}/context/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor, text: content })
    });
    openContextModal(content, data.answer || "", data.result || null);
    el("turn-input").value = "";
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    IS_SENDING_TURN = false;
    setBusy("submitTurnBtn", false, "...", CURRENT_ACTION_TYPE === "context" ? "Frage stellen" : "Zug senden");
  }
}

async function continueStory() {
  if (IS_SENDING_TURN || isSharedBlocking()) return;
  const actor = claimedSlotId();
  if (!actor || !campaignHasIntro()) return;
  IS_SENDING_TURN = true;
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor,
        mode: "STORY",
        text: CONTINUE_STORY_MARKER
      })
    });
    applyCampaign(data.campaign);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    IS_SENDING_TURN = false;
  }
}

async function retryCampaignIntro() {
  if (!SESSION.campaignId || !isHost() || isSharedBlocking()) return;
  setBusy("retryIntroBtn", true, "Versuche...");
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/intro/retry`, { method: "POST" });
    applyCampaign(data.campaign);
    if (data.turn) {
      showFlash("Der Kampagnenauftakt wurde erfolgreich erzeugt.");
    } else {
      showFlash(data.intro_state?.last_error || "Der Auftakt konnte noch nicht erzeugt werden.", true);
    }
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setBusy("retryIntroBtn", false, "...", "Auftakt erneut versuchen");
  }
}

function openEditModal(turnId) {
  const turn = (CAMPAIGN.active_turns || []).find((entry) => entry.turn_id === turnId);
  if (!turn) return;
  EDIT_TURN_ID = turnId;
  el("edit-player-text").value = turn.input_text_display;
  el("edit-gm-text").value = turn.gm_text_display;
  el("edit-modal").classList.remove("hidden");
  scheduleEditPresence(turnId);
}

function closeEditModal() {
  clearPresenceActivity();
  EDIT_TURN_ID = null;
  el("edit-modal").classList.add("hidden");
}

async function saveEdit() {
  if (!EDIT_TURN_ID || isSharedBlocking()) return;
  setBusy("saveEditBtn", true, "Speichere...");
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/turns/${EDIT_TURN_ID}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_text_display: el("edit-player-text").value,
        gm_text_display: el("edit-gm-text").value
      })
    });
    closeEditModal();
    applyCampaign(data.campaign);
    showFlash("Turn wurde editiert.");
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setBusy("saveEditBtn", false, "...", "Edit speichern");
  }
}

async function undoTurn(turnId) {
  if (isSharedBlocking()) return;
  if (!confirm("Diesen Turn und alle späteren aktiven Turns wirklich undoen?")) return;
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/turns/${turnId}/undo`, { method: "POST" });
    applyCampaign(data.campaign);
    showFlash("Turn wurde rückgängig gemacht.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function retryTurn(turnId) {
  if (isSharedBlocking()) return;
  if (!confirm("Diesen Turn ab seinem Vorzustand neu aufbauen?")) return;
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/turns/${turnId}/retry`, { method: "POST" });
    applyCampaign(data.campaign);
    showFlash("Turn wurde neu aufgebaut.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

function commaTags(value) {
  return value.split(",").map((tag) => tag.trim()).filter(Boolean);
}

async function savePlotEssentials() {
  try {
    const data = await api(`/api/campaigns/${SESSION.campaignId}/boards/plot-essentials`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        premise: el("plot-premise").value,
        current_goal: el("plot-goal").value,
        current_threat: el("plot-threat").value,
        active_scene: el("plot-scene").value,
        open_loops: el("plot-loops").value.split("\n").map((line) => line.trim()).filter(Boolean),
        tone: el("plot-tone").value
      })
    });
    applyCampaign(data.campaign);
    showFlash("Plot Essentials gespeichert.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function saveAuthorsNote() {
  try {
    const data = await api(`/api/campaigns/${SESSION.campaignId}/boards/authors-note`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: el("authors-note-input").value })
    });
    applyCampaign(data.campaign);
    showFlash("Author's Note gespeichert.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function savePlayerDiary() {
  const playerId = currentPlayer();
  const input = el("player-diary-input");
  if (!playerId || !input || isSharedBlocking()) return;
  try {
    const data = await api(`/api/campaigns/${SESSION.campaignId}/boards/diary/${playerId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: input.value })
    });
    applyCampaign(data.campaign);
    showFlash("Diary gespeichert.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function saveStoryCard() {
  const payload = {
    title: el("story-card-title").value.trim(),
    kind: el("story-card-kind").value.trim(),
    content: el("story-card-content").value.trim(),
    tags: commaTags(el("story-card-tags").value)
  };
  if (!payload.title || !payload.kind || !payload.content) {
    showFlash("Bitte Story Card vollständig ausfüllen.", true);
    return;
  }
  try {
    const path = EDITING_STORY_CARD_ID
      ? `/api/campaigns/${SESSION.campaignId}/boards/story-cards/${EDITING_STORY_CARD_ID}`
      : `/api/campaigns/${SESSION.campaignId}/boards/story-cards`;
    const method = EDITING_STORY_CARD_ID ? "PATCH" : "POST";
    const data = await api(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    EDITING_STORY_CARD_ID = null;
    applyCampaign(data.campaign);
    showFlash("Story Card gespeichert.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function saveWorldInfo() {
  const payload = {
    title: el("world-title").value.trim(),
    category: el("world-category").value.trim(),
    content: el("world-content").value.trim(),
    tags: commaTags(el("world-tags").value)
  };
  if (!payload.title || !payload.category || !payload.content) {
    showFlash("Bitte World Info vollständig ausfüllen.", true);
    return;
  }
  try {
    const path = EDITING_WORLD_INFO_ID
      ? `/api/campaigns/${SESSION.campaignId}/boards/world-info/${EDITING_WORLD_INFO_ID}`
      : `/api/campaigns/${SESSION.campaignId}/boards/world-info`;
    const method = EDITING_WORLD_INFO_ID ? "PATCH" : "POST";
    const data = await api(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    EDITING_WORLD_INFO_ID = null;
    applyCampaign(data.campaign);
    showFlash("World Info gespeichert.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function saveSessionMeta() {
  if (!SESSION_MODAL_ID) return;
  const entry = libraryEntry(SESSION_MODAL_ID);
  if (!entry) return;
  const previousSession = { ...SESSION };
  try {
    setActiveSession(entry);
    const data = await api(`/api/campaigns/${SESSION_MODAL_ID}/meta`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: el("session-modal-title").value.trim() || "Unbenannte Session" })
    });
    upsertSessionLibrary({ ...entry, title: data.campaign.campaign_meta.title });
    if (CAMPAIGN?.campaign_meta?.campaign_id === SESSION_MODAL_ID) CAMPAIGN = data.campaign;
    saveSession(previousSession);
    renderSessionLibrary();
    if (CAMPAIGN?.campaign_meta?.campaign_id === SESSION_MODAL_ID) renderCampaignView();
    closeSessionModal();
    showFlash("Session-Name gespeichert.");
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    saveSession(previousSession);
  }
}

async function saveCurrentSessionMeta() {
  if (!CAMPAIGN || !isHost()) return;
  try {
    const data = await api(`/api/campaigns/${SESSION.campaignId}/meta`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: el("settings-session-title").value.trim() || "Unbenannte Session" })
    });
    applyCampaign(data.campaign);
    showFlash("Session-Name gespeichert.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function exportSession() {
  if (!SESSION_MODAL_ID) return;
  const entry = libraryEntry(SESSION_MODAL_ID);
  if (!entry) return;
  const previousSession = { ...SESSION };
  try {
    setActiveSession(entry);
    const data = await api(`/api/campaigns/${SESSION_MODAL_ID}/export`);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(entry.title || "session").replace(/[^\w\-]+/g, "_")}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showFlash("Session exportiert.");
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    saveSession(previousSession);
  }
}

async function exportCurrentSession() {
  if (!CAMPAIGN) return;
  try {
    const data = await api(`/api/campaigns/${SESSION.campaignId}/export`);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(CAMPAIGN.campaign_meta.title || "session").replace(/[^\w\-]+/g, "_")}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showFlash("Session exportiert.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function deleteSession() {
  if (!SESSION_MODAL_ID) return;
  const entry = libraryEntry(SESSION_MODAL_ID);
  if (!entry) return;
  if (!confirm(`Session "${entry.title || entry.campaignId}" wirklich löschen?`)) return;
  const previousSession = { ...SESSION };
  try {
    setActiveSession(entry);
    await api(`/api/campaigns/${SESSION_MODAL_ID}`, { method: "DELETE" });
    if (previousSession.campaignId && previousSession.campaignId !== SESSION_MODAL_ID) saveSession(previousSession);
    else {
      clearSession();
      CAMPAIGN = null;
    }
    removeSessionLibraryEntry(SESSION_MODAL_ID);
    closeSessionModal();
    renderLanding();
    showFlash("Session gelöscht.");
  } catch (error) {
    showFlash(error.message, true);
    if (previousSession.campaignId && previousSession.campaignId !== SESSION_MODAL_ID) saveSession(previousSession);
  }
}

async function deleteCurrentSession() {
  if (!CAMPAIGN || !isHost()) return;
  if (!confirm(`Session "${CAMPAIGN.campaign_meta.title}" wirklich löschen?`)) return;
  try {
    await api(`/api/campaigns/${SESSION.campaignId}`, { method: "DELETE" });
    removeSessionLibraryEntry(SESSION.campaignId);
    closeSettingsModal();
    clearSession();
    CAMPAIGN = null;
    renderLanding();
    showFlash("Session gelöscht.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

function leaveSession() {
  clearPresenceActivity();
  clearSession();
  resetLiveState();
  CAMPAIGN = null;
  EDITING_STORY_CARD_ID = null;
  EDITING_WORLD_INFO_ID = null;
  closeEditModal();
  closeSetupModal();
  closeSessionModal();
  closeSettingsModal();
  closeCharacterDrawer();
  closeContextModal();
  renderLanding();
}

function setActiveSession(entry) {
  saveSession({
    campaignId: entry.campaignId,
    playerId: entry.playerId,
    playerToken: entry.playerToken,
    joinCode: entry.joinCode
  });
}

document.addEventListener("click", (event) => {
  const target = event.target;
  const actionTarget = target.closest("[data-action]");
  if (target.id === "savePlotBtn") savePlotEssentials();
  if (target.id === "saveAuthorsNoteBtn") saveAuthorsNote();
  if (target.id === "savePlayerDiaryBtn") savePlayerDiary();
  if (target.id === "saveStoryCardBtn") saveStoryCard();
  if (target.id === "saveWorldInfoBtn") saveWorldInfo();
  if (target.id === "exportAttributeChartBtn") exportAttributeChartPng();
  if (target.id === "saveSettingsSessionBtn") saveCurrentSessionMeta();
  if (target.id === "exportSettingsSessionBtn") exportCurrentSession();
  if (target.id === "deleteSettingsSessionBtn") deleteCurrentSession();
  if (target.id === "cancelStoryCardEditBtn") {
    EDITING_STORY_CARD_ID = null;
    renderStoryCardsTab();
  }
  if (target.id === "cancelWorldInfoEditBtn") {
    EDITING_WORLD_INFO_ID = null;
    renderWorldInfoTab();
  }
  if (target.matches(".action-mode")) setActionMode(target.dataset.mode);
  if (target.matches(".tab")) setActiveSidebarTab(target.dataset.tab);
  if (target.matches(".codex-subtab")) setActiveCodexTab(target.dataset.codexTab);
  if (target.matches(".settings-tab")) setActiveSettingsTab(target.dataset.tab);
  if (target.matches(".drawer-tab")) setDrawerTab(target.dataset.drawerTab);
  if (actionTarget?.dataset.action === "set-theme") setTheme(actionTarget.dataset.theme);
  if (actionTarget?.dataset.action === "set-font-preset") setFontPreset(actionTarget.dataset.fontPreset);
  if (actionTarget?.dataset.action === "set-font-size") setFontSize(actionTarget.dataset.fontSize);
  if (actionTarget?.dataset.action === "reroll-preview-answer") rerollSetupPreviewAnswer(actionTarget.dataset.index);
  if (actionTarget?.dataset.action === "claim-slot") claimSlot(actionTarget.dataset.slotId);
  if (actionTarget?.dataset.action === "take-slot") takeOverSlot(actionTarget.dataset.slotId);
  if (actionTarget?.dataset.action === "open-character-sheet") openCharacterDrawer(actionTarget.dataset.slotId, actionTarget.dataset.openTab || "overview").catch((error) => showFlash(error.message, true));
  if (actionTarget?.dataset.action === "open-npc-sheet") openNpcDrawer(actionTarget.dataset.npcId, actionTarget.dataset.openTab || "overview").catch((error) => showFlash(error.message, true));
  if (actionTarget?.dataset.action === "open-codex-entry") openCodexDrawer(actionTarget.dataset.codexKind, actionTarget.dataset.codexId, actionTarget.dataset.openTab || "overview").catch((error) => showFlash(error.message, true));
  if (actionTarget?.dataset.action === "edit-turn") openEditModal(actionTarget.dataset.turnId);
  if (actionTarget?.dataset.action === "undo-turn") undoTurn(actionTarget.dataset.turnId);
  if (actionTarget?.dataset.action === "retry-turn") retryTurn(actionTarget.dataset.turnId);
  if (actionTarget?.dataset.action === "continue-turn") continueStory();
  if (actionTarget?.dataset.action === "open-session") openSavedSession(actionTarget.dataset.campaignId);
  if (actionTarget?.dataset.action === "edit-session") openSessionModal(actionTarget.dataset.campaignId);
  if (actionTarget?.dataset.action === "forget-session") forgetSession(actionTarget.dataset.campaignId);
  if (actionTarget?.dataset.action === "edit-story-card") {
    EDITING_STORY_CARD_ID = actionTarget.dataset.cardId;
    renderStoryCardsTab();
  }
  if (actionTarget?.dataset.action === "edit-world-entry") {
    EDITING_WORLD_INFO_ID = actionTarget.dataset.entryId;
    renderWorldInfoTab();
  }
  if (target.id === "character-drawer") closeCharacterDrawer();
  if (target.id === "context-modal") closeContextModal();
  if (target.id === "setup-random-modal") closeSetupRandomModal();
});

el("createCampaignBtn").addEventListener("click", createCampaign);
el("joinCampaignBtn").addEventListener("click", joinCampaign);
el("submitTurnBtn").addEventListener("click", submitTurn);
el("saveEditBtn").addEventListener("click", saveEdit);
el("cancelEditBtn").addEventListener("click", closeEditModal);
el("closeEditModalBtn").addEventListener("click", closeEditModal);
el("claimBackBtn").addEventListener("click", leaveSession);
el("leaveBtn").addEventListener("click", leaveSession);
el("unclaimBtn").addEventListener("click", unclaimCurrentSlot);
el("openSettingsBtn").addEventListener("click", () => openSettingsModal("session"));
el("openLandingSettingsBtn").addEventListener("click", () => openSettingsModal("style"));
el("closeSessionModalBtn").addEventListener("click", closeSessionModal);
el("closeSettingsModalBtn").addEventListener("click", closeSettingsModal);
el("closeCharacterDrawerBtn").addEventListener("click", closeCharacterDrawer);
el("closeContextModalBtn").addEventListener("click", closeContextModal);
el("setupRandomBtn").addEventListener("click", openSetupRandomModal);
el("closeSetupRandomModalBtn").addEventListener("click", closeSetupRandomModal);
el("setupRandomRerollBtn").addEventListener("click", () => loadSetupRandomPreview(currentSetupRandomMode()));
el("setupRandomApplyBtn").addEventListener("click", applySetupRandomPreview);
el("saveSessionMetaBtn").addEventListener("click", saveSessionMeta);
el("exportSessionBtn").addEventListener("click", exportSession);
el("deleteSessionBtn").addEventListener("click", deleteSession);
el("setupPrevBtn").addEventListener("click", previousSetupStep);
el("setupSkipBtn").addEventListener("click", () => submitSetupAnswer(true));
el("setupSubmitBtn").addEventListener("click", () => submitSetupAnswer(false));
el("retryIntroBtn").addEventListener("click", retryCampaignIntro);

el("turn-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitTurn();
  }
});
el("turn-input").addEventListener("input", scheduleTypingPresence);
el("turn-input").addEventListener("blur", () => clearPresenceActivity());

["create-name", "create-title"].forEach((id) => {
  el(id).addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      createCampaign();
    }
  });
});

["join-name", "join-code"].forEach((id) => {
  el(id).addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      joinCampaign();
    }
  });
});

document.querySelectorAll('input[name="setup-random-mode"]').forEach((input) => {
  input.addEventListener("change", () => {
    if (!el("setup-random-modal").classList.contains("hidden")) {
      loadSetupRandomPreview(currentSetupRandomMode());
    }
  });
});

document.addEventListener("input", (event) => {
  const target = event.target;
  if (!target) return;
  if (target.id === "edit-player-text" || target.id === "edit-gm-text") {
    scheduleEditPresence();
    return;
  }
  if (!el("setup-modal").classList.contains("hidden")) {
    if (
      String(target.id || "").startsWith("setup-answer")
      || target.classList?.contains("setup-answer-multi")
      || target.classList?.contains("setup-answer-select-choice")
    ) {
      scheduleSetupPresence();
    }
  }
});

document.addEventListener("change", (event) => {
  const target = event.target;
  if (!target) return;
  if (!el("setup-modal").classList.contains("hidden")) {
    if (
      String(target.id || "").startsWith("setup-answer")
      || target.classList?.contains("setup-answer-multi")
      || target.classList?.contains("setup-answer-select-choice")
      || target.name === "setup-boolean"
    ) {
      scheduleSetupPresence();
    }
  }
});

document.addEventListener("mouseover", (event) => {
  const target = event.target;
  if (!target) return;
  const highlighted = target.closest?.(".story-response.turn-highlight");
  if (!highlighted) return;
  clearRecentTurnHighlight(highlighted.dataset.turnId || null);
});

bootstrap();

async function bootstrap() {
  applyTheme(CURRENT_THEME);
  applyFontPreset(CURRENT_FONT_PRESET);
  applyFontSize(CURRENT_FONT_SIZE);
  applyDrawerTabLayout("pc");
  setActiveSidebarTab("chars");
  setActiveSettingsTab("session");
  setActionMode("do");
  if (SESSION.campaignId && SESSION.playerId && SESSION.playerToken) {
    await loadCampaign();
    return;
  }
  renderLanding();
}

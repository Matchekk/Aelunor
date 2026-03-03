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
let ACTIVE_DRAWER_TAB = "overview";
let ACTIVE_SIDEBAR_TAB = "chars";
let ACTIVE_SETTINGS_TAB = "session";
let CURRENT_THEME = loadTheme();
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
};

const ACTION_MODE_CONFIG = {
  do: { placeholder: "Was tut deine Figur konkret?" },
  say: { placeholder: "Was sagt deine Figur?" },
  story: { placeholder: "Welche Story-Richtung oder welchen Fokus willst du setzen?" }
};

const SIDEBAR_TAB_IDS = ["chars", "map", "events"];
const SETTINGS_TAB_IDS = ["style", "plot", "note", "cards", "world", "memory", "session"];
const TAB_IDS = [...SETTINGS_TAB_IDS, ...SIDEBAR_TAB_IDS];
const THEME_LABELS = {
  arcane: "Nachtblau",
  tavern: "Taverne"
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
  return stored === "tavern" ? "tavern" : "arcane";
}

function saveTheme(themeId) {
  localStorage.setItem("isekaiTheme", themeId);
}

function applyTheme(themeId) {
  CURRENT_THEME = themeId === "tavern" ? "tavern" : "arcane";
  document.documentElement.dataset.theme = CURRENT_THEME;
}

function setTheme(themeId) {
  applyTheme(themeId);
  saveTheme(CURRENT_THEME);
  renderBoards();
  showFlash(`Style gewechselt: ${THEME_LABELS[CURRENT_THEME] || "Style"}`);
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
  LIVE_STATE.reloadTimer = null;
  LIVE_STATE.typingTimer = null;
  LIVE_STATE.setupTimer = null;
  LIVE_STATE.editTimer = null;
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
    if (path.includes("/random")) return "Der GM würfelt die Welt gerade aus...";
    return "Die Welt wird gerade definiert...";
  }
  if (path.includes("/slots/") && path.includes("/setup/")) {
    if (path.includes("/random")) return "Der GM würfelt die Figur gerade aus...";
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
  bar.className = `live-activity-bar${blocking ? " blocking" : ""}`;
  bar.innerHTML = `
    <div class="live-activity-icon" aria-hidden="true"></div>
    <div class="live-activity-copy">
      <strong>${escapeHtml(status)}</strong>
      <span>${escapeHtml(active.label || "Jemand ist aktiv...")}</span>
    </div>
    <div class="live-activity-state">${LIVE_STATE.sseConnected ? "Verbunden" : "Verbindung wird erneuert..."}</div>
  `;
}

function renderLiveDecorations() {
  renderLoadingOverlay();
  renderActivityBar();
  if (CAMPAIGN && !el("claim-view").classList.contains("hidden")) renderClaimView();
  if (CAMPAIGN && !el("campaign-view").classList.contains("hidden")) {
    renderPartyOverview();
    const claimed = claimedSlot();
    el("claimed-actor-badge").textContent = claimed ? `Du spielst ${claimed.display_name || claimed.slot_id}` : "Kein Claim";
  }
}

function titleizeToken(value) {
  const lowered = (value || "").toString().toLowerCase();
  const map = {
    hp: "HP",
    stamina: "Ausdauer",
    aether: "Aether",
    stress: "Stress",
    corruption: "Verderbnis",
    wounds: "Wunden",
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
    do: "Tun",
    say: "Sagen",
    story: "Story"
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

function renderTurns() {
  const root = el("turns");
  const turns = CAMPAIGN?.active_turns || [];
  if (!turns.length) {
    const intro = introState();
    const message = CAMPAIGN?.state?.meta?.phase === "adventure"
      ? intro.status === "failed"
        ? "Der Auftakt fehlt noch. Versuche ihn erneut, bevor neue Beiträge gesendet werden."
        : "Die Geschichte wartet auf den ersten GM-Auftakt."
      : "Sobald Welt und Figuren fertig sind, eröffnet der GM die erste Szene.";
    root.innerHTML = `<div class="empty-state small">${message}</div>`;
    return;
  }
  const latestTurnId = turns[turns.length - 1]?.turn_id;
  root.innerHTML = turns.map((turn) => `
    <article class="turn-card">
      <div class="story-meta">
        <span>${formatDate(turn.created_at)}</span>
        ${turn.edit_count ? `<span>${turn.edit_count} Edit${turn.edit_count > 1 ? "s" : ""}</span>` : ""}
      </div>
      <div class="story-input">
        <div class="story-input-labels">
          <span class="story-speaker">${escapeHtml(contributionLabel(turn))}</span>
          <span class="type-badge type-${escapeHtml(turn.action_type)}">${escapeHtml(actionTypeLabel(turn.action_type))}</span>
        </div>
        <div class="story-input-text">${escapeHtml(contributionText(turn))}</div>
      </div>
      <div class="story-response">
        ${escapeHtml(turn.gm_text_display)}
      </div>
      <div class="turn-actions">
        ${turn.can_edit ? `<button class="btn ghost" data-action="edit-turn" data-turn-id="${turn.turn_id}" type="button">Edit</button>` : ""}
        ${turn.can_undo ? `<button class="btn ghost" data-action="undo-turn" data-turn-id="${turn.turn_id}" type="button">Undo</button>` : ""}
        ${turn.can_retry ? `<button class="btn ghost" data-action="retry-turn" data-turn-id="${turn.turn_id}" type="button">Retry</button>` : ""}
        ${(turn.turn_id === latestTurnId && claimedSlotId()) ? `<button class="btn primary" data-action="continue-turn" type="button">Weiter</button>` : ""}
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
    const buttonDisabled = locked || Boolean(mine && !mineSlot);
    const activity = slot.claimed_by ? LIVE_STATE.activitiesByPlayer[slot.claimed_by] : null;
    const status = slot.claimed_by ? (mineSlot ? "Du" : `Von ${slot.claimed_by_name || "jemandem"} gespielt`) : "Frei";
    const label = slot.completed ? slot.display_name : `Slot ${slot.slot_id.split("_")[1]}`;
    const summary = slot.completed
      ? `${slot.summary.party_role || "Ohne Rolle"} • ${slot.summary.current_focus || "Ohne Fokus"}`
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
        <button class="btn ${mineSlot ? "primary" : "ghost"}" data-action="claim-slot" data-slot-id="${slot.slot_id}" type="button" ${buttonDisabled ? "disabled" : ""}>
          ${mineSlot ? "Weiter mit diesem Slot" : mine && !mineSlot ? "Bereits anderer Claim" : "Slot claimen"}
        </button>
      </div>
    `;
  }).join("");
}

function renderPartyOverview() {
  const root = el("party-overview");
  const cards = CAMPAIGN?.party_overview || [];
  if (!cards.length) {
    root.innerHTML = `<div class="empty-state small">Noch keine Party-Slots sichtbar.</div>`;
    return;
  }
  root.innerHTML = cards.map((card) => `
    <button class="party-card ${card.slot_id === claimedSlotId() ? "is-self" : ""}" data-action="open-character-sheet" data-slot-id="${card.slot_id}" type="button">
      <div class="party-card-head">
        <div>
          <div class="party-card-name">${escapeHtml(card.display_name || card.slot_id)}</div>
          <div class="small party-card-subline">${escapeHtml(card.scene_name || "Kein Ort")}</div>
        </div>
        <span class="badge">${card.slot_id === claimedSlotId() ? "Du" : (card.claimed_by ? `Von ${card.claimed_by_name || "jemandem"}` : "Frei")}</span>
      </div>
      <div class="party-activity ${cardActivity(card) ? "" : "is-idle"}">${escapeHtml(cardActivity(card)?.label || (card.claimed_by ? "Gerade ruhig." : "Wartet auf einen Spieler."))}</div>
      <div class="resource-row">
        <span>HP ${escapeHtml(card.hp)}</span>
        <span>STA ${escapeHtml(card.stamina)}</span>
        <span>Aether ${escapeHtml(card.aether)}</span>
      </div>
      <div class="resource-row">
        <span>Wunden ${escapeHtml(card.wounds)}</span>
        <span>Traglast ${escapeHtml(card.carry)}</span>
      </div>
      <div class="small">${escapeHtml(card.age ? `${card.age} • ${ageStageLabel(card.age_stage)}` : ageStageLabel(card.age_stage))}</div>
      <div class="small">${escapeHtml(card.appearance_short || "Unauffällig")}</div>
      <div class="condition-pills">
        ${(card.conditions || []).slice(0, 3).map((condition) => `<span class="mini-pill">${escapeHtml(condition)}</span>`).join("")}
        ${card.in_combat ? `<span class="mini-pill">Im Kampf</span>` : ""}
      </div>
    </button>
  `).join("");
}

function setDrawerTab(tabId) {
  ACTIVE_DRAWER_TAB = tabId;
  document.querySelectorAll(".drawer-tab").forEach((button) => button.classList.toggle("active", button.dataset.drawerTab === tabId));
  ["overview", "stats", "skills", "abilities", "gear", "effects", "journal"].forEach((id) => {
    el(`drawer-panel-${id}`).classList.toggle("hidden", id !== tabId);
  });
}

function detailRow(label, value) {
  const safeValue = value === undefined || value === null || value === "" ? "-" : String(value);
  return `<div class="small"><strong>${escapeHtml(label)}:</strong> ${escapeHtml(safeValue)}</div>`;
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

function renderCharacterDrawer() {
  if (!CHARACTER_SHEET) return;
  const sheet = CHARACTER_SHEET.sheet || {};
  const overview = sheet.overview || {};
  const stats = sheet.stats || {};
  const progression = sheet.progression || {};
  const appearance = overview.appearance || {};
  const ageing = overview.ageing || {};
  const metaInfo = sheet.meta || {};
  el("drawer-title").textContent = CHARACTER_SHEET.display_name || CHARACTER_SHEET.slot_id;
  el("drawer-subtitle").textContent = `${CHARACTER_SHEET.scene_name || "Kein Ort"} • ${CHARACTER_SHEET.claimed_by_name || "Nicht geclaimt"}`;

  el("drawer-panel-overview").innerHTML = `
    <details class="accordion" open>
      <summary>Identität</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Name", overview.bio?.name)}
          ${detailRow("Geschlecht", overview.bio?.gender)}
          ${detailRow("Alter", `${overview.bio?.age_years ?? "-"} • ${ageStageLabel(overview.bio?.age_stage)}`)}
          ${detailRow("Rolle", overview.bio?.party_role)}
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
        ${["hp", "stamina", "aether", "stress", "corruption", "wounds"].map((key) => `
          <div class="stat-card">
            <strong>${escapeHtml(titleizeToken(key))}</strong>
            <div>${(overview.resources?.[key]?.current ?? 0)}/${(overview.resources?.[key]?.max ?? 0)}</div>
          </div>
        `).join("")}
      </div>
    </details>
    <details class="accordion">
      <summary>Progression</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("System-Stufe", progression.system_level)}
          ${detailRow("System XP", `${progression.system_xp ?? 0}/${progression.next_system_xp ?? 0}`)}
          ${detailRow("Rang", progression.rank)}
          ${detailRow("System-Fragmente", progression.system_fragments)}
          ${detailRow("System-Kerne", progression.system_cores)}
          ${detailRow("Attributspunkte", progression.attribute_points)}
          ${detailRow("Fertigkeitspunkte", progression.skill_points)}
          ${detailRow("Talentpunkte", progression.talent_points)}
        </div>
        <div class="sheet-block">
          ${detailRow("Pfade", (progression.paths || []).map((path) => path.name || path.id).join(", "))}
          ${detailRow("Potenzialkarten", (progression.potential_cards || []).map((card) => card.name || card.id).join(", "))}
          ${detailRow("Klasse", metaInfo.class_state?.class_name || metaInfo.class_state?.class_id)}
          ${detailRow("Fraktionen", (metaInfo.faction_memberships || []).filter((entry) => entry.active !== false).map((entry) => entry.name || entry.faction_id).join(", "))}
        </div>
      </div>
    </details>
  `;

  el("drawer-panel-stats").innerHTML = `
    <details class="accordion" open>
      <summary>Attribute</summary>
      <div class="accordion-body stat-grid">
        ${Object.entries(stats.attributes || {}).map(([key, value]) => `<div class="stat-card"><strong>${escapeHtml(key.toUpperCase())}</strong><div>${value}</div></div>`).join("")}
      </div>
    </details>
    <details class="accordion" open>
      <summary>Abgeleitete Werte</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Verteidigung", stats.derived?.defense)}
          ${detailRow("Verteidigungs-Bonus", stats.modifier_summary?.defense)}
          ${detailRow("Rüstung", stats.derived?.armor)}
          ${detailRow("Initiative", stats.derived?.initiative)}
          ${detailRow("Initiative-Bonus", stats.modifier_summary?.initiative)}
          ${detailRow("Angriff Hauptwaffe", stats.derived?.attack_rating_mainhand)}
          ${detailRow("Bonus Hauptwaffe", stats.modifier_summary?.attack_rating_mainhand)}
          ${detailRow("Angriff Nebenhand", stats.derived?.attack_rating_offhand)}
          ${detailRow("Bonus Nebenhand", stats.modifier_summary?.attack_rating_offhand)}
          ${detailRow("Traglast", `${stats.derived?.carry_weight ?? 0}/${stats.derived?.carry_limit ?? 0}`)}
          ${detailRow("Belastung", encumbranceLabel(stats.derived?.encumbrance_state))}
        </div>
        <div class="sheet-block">
          ${Object.entries(stats.resistances || {}).map(([key, value]) => detailRow(titleizeToken(key), value)).join("")}
        </div>
      </div>
    </details>
    <details class="accordion">
      <summary>Alterungsmodifikatoren</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("Stufe", ageStageLabel(stats.age_modifiers?.stage))}
          ${detailRow("HP-Max", stats.age_modifiers?.resource_deltas?.hp_max)}
          ${detailRow("STA-Max", stats.age_modifiers?.resource_deltas?.stamina_max)}
        </div>
        <div class="sheet-block">
          ${detailRow("Skill-Boni", Object.entries(stats.age_modifiers?.skill_bonuses || {}).map(([key, value]) => `${titleizeToken(key)} +${value}`).join(", "))}
          ${detailRow("Hinweise", (stats.age_modifiers?.notes || []).join(", "))}
        </div>
      </div>
    </details>
  `;

  el("drawer-panel-skills").innerHTML = `
    <details class="accordion" open>
      <summary>Fertigkeitssystem</summary>
      <div class="accordion-body sheet-grid">
        <div class="sheet-block">
          ${detailRow("System-Stufe", progression.system_level)}
          ${detailRow("System XP", `${progression.system_xp ?? 0}/${progression.next_system_xp ?? 0}`)}
          ${detailRow("Fertigkeitspunkte", progression.skill_points)}
          ${detailRow("Talentpunkte", progression.talent_points)}
        </div>
        <div class="sheet-block">
          ${detailRow("System-Fragmente", progression.system_fragments)}
          ${detailRow("System-Kerne", progression.system_cores)}
          ${detailRow("Pfade", (progression.paths || []).map((path) => path.name || path.id).join(", "))}
          ${detailRow("Potenzialkarten", (progression.potential_cards || []).map((card) => card.name || card.id).join(", "))}
        </div>
      </div>
    </details>
    <details class="accordion" open>
      <summary>Fertigkeiten</summary>
      <div class="accordion-body skill-list">
        ${(sheet.skills || []).length ? (sheet.skills || []).map((skill) => `
          <details class="skill-card">
            <summary>
              <div class="skill-card-head">
                <div>
                  <strong>${escapeHtml(skill.name || titleizeToken(skill.id))}</strong>
                  <div class="small">Stufe ${skill.level ?? 1} • Attribut ${escapeHtml(titleizeToken(skill.attribute || ""))} • Effektiv +${skill.effective_bonus ?? 0}${(skill.modifier_bonus ?? 0) ? ` • Modifikator +${skill.modifier_bonus}` : ""}</div>
                </div>
                <div class="inline-list">
                  <span class="rank-badge ${skillRankClass(skill.rank)}">${escapeHtml(skill.rank || "F")}</span>
                  ${skill.path ? `<span class="mini-pill">${escapeHtml(skill.path)}</span>` : ""}
                  ${skill.awakened ? `<span class="mini-pill">Erwacht</span>` : ""}
                </div>
              </div>
            </summary>
            <div class="accordion-body">
              ${meterMarkup("XP", skill.xp, skill.next_xp)}
              <div class="sheet-grid" style="margin-top:12px">
                <div class="sheet-block">
                  ${detailRow("Mastery", `${skill.mastery ?? 0}%`)}
                  ${detailRow("Pfad", skill.path || (skill.path_choice_available ? "Auswahl verfügbar" : "-"))}
                  ${detailRow("Nächste Entwicklung", (skill.evolutions || [])[0] || "-")}
                </div>
                <div class="sheet-block">
                  ${detailRow("Entwicklungen", (skill.evolutions || []).join(", "))}
                  ${detailRow("Fusionen", (skill.fusion_candidates || []).map((entry) => entry.result).join(", "))}
                  ${detailRow("Freischaltungen", (skill.unlocks || []).join(", "))}
                </div>
              </div>
              ${skill.path_choice_available ? `<div class="readonly-note" style="margin-top:12px"><strong>Pfadauswahl verfügbar:</strong> ${(skill.path_options || []).map(escapeHtml).join(" • ")}</div>` : ""}
              ${(skill.fusion_candidates || []).length ? `
                <div class="skill-fusion-list">
                  ${(skill.fusion_candidates || []).map((entry) => `
                    <div class="inventory-item">
                      <strong>${escapeHtml(entry.result || "-")}</strong><br/>
                      <span class="small">Fusion mit ${escapeHtml(entry.with_display || titleizeToken(entry.with || ""))} • Rank ${escapeHtml(entry.rank || "S")} • braucht ${entry.requires_core ?? 1} System Core</span>
                    </div>
                  `).join("")}
                </div>
              ` : ""}
            </div>
          </details>
        `).join("") : `<div class="small">Noch keine gelernten Skills. Start-Skills kommen erst über die Rollenwahl oder spätere Entwicklung.</div>`}
      </div>
    </details>
  `;

  el("drawer-panel-abilities").innerHTML = `
    <details class="accordion" open>
      <summary>Fähigkeiten</summary>
      <div class="accordion-body inventory-list">
        ${(sheet.abilities || []).length ? (sheet.abilities || []).map((ability) => `
          <div class="inventory-item">
            <strong>${escapeHtml(ability.name || ability.id)}</strong><br/>
            <span class="small">${escapeHtml(ability.type || "Fähigkeit")} • Kosten STA ${ability.cost?.stamina ?? ability.charges ?? 0} • Aether ${ability.cost?.aether ?? 0} • Abklingzeit ${ability.cooldown_turns ?? 0}</span><br/>
            <span class="small">${escapeHtml(ability.description || "")}</span>
          </div>
        `).join("") : `<div class="small">Noch keine Fähigkeiten.</div>`}
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

  el("drawer-panel-effects").innerHTML = `
    <details class="accordion" open>
      <summary>Effekte</summary>
      <div class="accordion-body inventory-list">
        ${(sheet.effects || []).length ? (sheet.effects || []).map((effect) => `
          <div class="inventory-item">
            <strong>${escapeHtml(effect.name || effect.id)}</strong><br/>
            <span class="small">${escapeHtml(effect.category || "Effekt")} • Dauer ${effect.duration_turns ?? 0} • Intensität ${effect.intensity ?? 0}</span><br/>
            <span class="small">${escapeHtml(effect.description || "")}</span>
          </div>
        `).join("") : `<div class="small">Keine aktiven Effekte.</div>`}
      </div>
    </details>
  `;

  el("drawer-panel-journal").innerHTML = `
    <details class="accordion" open>
      <summary>Journal-Notizen</summary>
      <div class="accordion-body inventory-list">
        ${(sheet.journal?.notes || []).length ? (sheet.journal.notes || []).map((entry) => `<div class="inventory-item">${escapeHtml(entry.text || entry.title || JSON.stringify(entry))}</div>`).join("") : `<div class="small">Noch keine Notizen.</div>`}
      </div>
    </details>
    <details class="accordion" open>
      <summary>Aussehensverlauf</summary>
      <div class="accordion-body inventory-list">
        ${(sheet.journal?.appearance_history || []).length ? [...(sheet.journal.appearance_history || [])].reverse().map((entry) => `
          <div class="inventory-item">
            <strong>${escapeHtml(appearanceEventLabel(entry.kind))}</strong><br/>
            <span class="small">Tag ${entry.absolute_day ?? 0} • Turn ${entry.turn_number ?? 0}</span><br/>
            <span class="small">${escapeHtml(entry.message || entry.new_value || "")}</span>
          </div>
        `).join("") : `<div class="small">Noch keine sichtbaren Veränderungen.</div>`}
      </div>
    </details>
    <details class="accordion">
      <summary>NPC-Beziehungen</summary>
      <div class="accordion-body inventory-list">
        ${(sheet.journal?.npc_relationships || []).length ? (sheet.journal.npc_relationships || []).map((entry) => `<div class="inventory-item"><strong>${escapeHtml(entry.name || entry.npc_id)}</strong><br/><span class="small">${escapeHtml(entry.status || "")} • ${entry.score ?? 0}</span></div>`).join("") : `<div class="small">Noch keine NPC-Beziehungen.</div>`}
      </div>
    </details>
    <details class="accordion">
      <summary>Ruf & Plotpoints</summary>
      <div class="accordion-body inventory-list">
        ${(sheet.journal?.reputation || []).map((entry) => `<div class="inventory-item"><strong>${escapeHtml(entry.name || entry.faction_id)}</strong><br/><span class="small">${entry.score ?? 0} • ${escapeHtml(entry.status || "")}</span></div>`).join("")}
        ${(sheet.journal?.personal_plotpoints || []).map((entry) => `<div class="inventory-item"><strong>${escapeHtml(entry.title || entry.id)}</strong><br/><span class="small">${escapeHtml(entry.status || "")}</span></div>`).join("") || `<div class="small">Noch keine Einträge.</div>`}
      </div>
    </details>
  `;

  setDrawerTab(ACTIVE_DRAWER_TAB || "overview");
  el("character-drawer").classList.remove("hidden");
}

async function openCharacterDrawer(slotId) {
  const data = await api(`/api/campaigns/${SESSION.campaignId}/characters/${slotId}`);
  CHARACTER_SHEET = data;
  ACTIVE_DRAWER_TAB = "overview";
  renderCharacterDrawer();
}

function closeCharacterDrawer() {
  CHARACTER_SHEET = null;
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
      <strong>Rolle:</strong> ${isHost() ? "Host" : "Teilnehmer"}<br/>
      <strong>Aktualisiert:</strong> ${formatDate(CAMPAIGN.campaign_meta.updated_at)}
    </div>
    <div class="turn-actions">
      ${isHost() ? `<button class="btn primary" id="saveSettingsSessionBtn" type="button">Name speichern</button>` : ""}
      <button class="btn ghost" id="exportSettingsSessionBtn" type="button">Exportieren</button>
      ${isHost() ? `<button class="btn ghost" id="deleteSettingsSessionBtn" type="button">Löschen</button>` : ""}
    </div>
  `;
}

function renderCharactersTab() {
  const root = el("tab-chars");
  const chars = CAMPAIGN.party_overview || [];
  root.innerHTML = `
    <div class="panelTitle">Charaktere</div>
    <div class="info-grid">
      ${chars.map((card) => `
        <div class="info-item">
          <div class="entity-meta">
            <strong>${escapeHtml(card.display_name || card.slot_id.toUpperCase())}</strong>
            <span class="badge">${card.claimed_by ? "geclaimt" : "frei"}</span>
            ${card.scene_name ? `<span class="badge">${escapeHtml(card.scene_name)}</span>` : `<span class="badge muted-badge">keine Szene</span>`}
          </div>
          <div class="small">${escapeHtml(card.slot_id.toUpperCase())}</div>
          <div class="small">HP ${escapeHtml(card.hp)} • STA ${escapeHtml(card.stamina)} • Aether ${escapeHtml(card.aether)}</div>
          <div class="small">Rolle: ${escapeHtml(card.party_role || "-")}</div>
          <div class="small">Traglast: ${escapeHtml(card.carry || "-")}</div>
          <div class="turn-actions"><button class="btn ghost" data-action="open-character-sheet" data-slot-id="${card.slot_id}" type="button">Sheet öffnen</button></div>
        </div>
      `).join("")}
    </div>
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
    return `
      <div class="field">
        <span>${escapeHtml(question.label)}</span>
        <select id="setup-answer-select">
          <option value="">Bitte wählen</option>
          ${(question.options || []).map((option) => `<option value="${escapeHtml(option)}" ${selected === option ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}
          ${question.allow_other ? `<option value="__other__" ${selected === "Sonstiges" ? "selected" : ""}>Sonstiges</option>` : ""}
        </select>
      </div>
    `;
  }
  if (question.type === "multiselect") {
    const selected = new Set(answer?.selected || []);
    return `
      <div class="field">
        <span>${escapeHtml(question.label)}</span>
        <div class="setup-choice-list">
          ${(question.options || []).map((option) => `
            <label class="setup-choice">
              <input class="setup-answer-multi" type="checkbox" value="${escapeHtml(option)}" ${selected.has(option) ? "checked" : ""} />
              <span>${escapeHtml(option)}</span>
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
    return `<label class="field"><span>Sonstiges (nur ausfüllen, wenn du oben Sonstiges wählst)</span><input id="setup-answer-other" type="text" value="${escapeHtml(answer?.other_text || "")}" /></label>`;
  }
  if (question.type === "multiselect") {
    return `<label class="field"><span>Weitere Einträge (optional, durch Komma getrennt)</span><input id="setup-answer-other" type="text" value="${escapeHtml((answer?.other_values || []).join(", "))}" /></label>`;
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
  el("setupSubmitBtn").textContent = promptState.progress.step >= promptState.progress.total
    ? (SETUP_FLOW.mode === "world" ? "Run definieren" : "Figur abschließen")
    : "Antwort senden";
  el("setup-modal").classList.remove("hidden");
}

function openSetupFlow(mode, payload, slotId = null) {
  closeSetupModal();
  SETUP_FLOW = { mode, slotId, stack: [], index: -1 };
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
    const value = el("setup-answer-select").value;
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
    root.innerHTML = `<div class="empty-state small">Noch kein Vorschlag gewürfelt.</div>`;
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
            <button class="btn ghost random-inline-btn" data-action="reroll-preview-answer" data-index="${index}" type="button" aria-label="Nur diese Frage neu würfeln">🎲</button>
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
  setBusy("setupRandomBtn", true, "🎲");
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
    setBusy("setupRandomBtn", false, "...", "🎲");
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
    showFlash("Diese Frage wurde neu ausgewürfelt.");
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
          ? "Der ausgewürfelte Vorschlag wurde übernommen."
          : `${data.randomized_count} ausgewürfelte Antworten wurden übernommen.`
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
  el("campaign-title").textContent = meta.title;
  el("campaign-meta").textContent = `Turn ${state.meta.turn} • ${phaseLabel(state.meta.phase)}${worldBits.length ? ` • ${worldBits.join(" • ")}` : ""}`;
  el("join-code-chip").textContent = `Code: ${SESSION.joinCode || "gespeichert"}`;
  el("viewer-summary").textContent = `${viewer().display_name || "Spieler"} • ${isHost() ? "Host" : "Spieler"} • ${claimed?.display_name || claimed?.slot_id || "kein Claim"}${activeNames.length ? ` • Aktiv: ${activeNames.join(", ")}` : ""}`;
  el("claimed-actor-badge").textContent = claimed ? `Du spielst ${claimed.display_name || claimed.slot_id}` : "Kein Claim";
  el("unclaimBtn").disabled = !claimed;
  el("turn-input").disabled = !claimed || !isAdventure || !hasIntro;
  el("submitTurnBtn").disabled = !claimed || !isAdventure || !hasIntro;
  el("composer-hint").textContent = !isAdventure
    ? "Vor dem Abenteuer müssen Welt und alle benötigten Figuren abgeschlossen sein."
    : !hasIntro && intro.status === "failed"
    ? "Der Auftakt muss zuerst erfolgreich erzeugt werden, bevor du neue Beiträge senden kannst."
    : !hasIntro
    ? "Der GM bereitet gerade noch den ersten Szenenauftakt vor."
    : claimed
    ? `Der GM baut deinen ${actionTypeLabel(CURRENT_ACTION_TYPE)}-Beitrag direkt in die laufende Szene ein.`
    : "Ohne Claim kannst du lesen, aber keinen Turn senden.";
  renderIntroBanner();
  renderTurns();
  renderPartyOverview();
  renderBoards();
  renderActivityBar();
  setActiveSidebarTab(ACTIVE_SIDEBAR_TAB || "chars");
  setActionMode(CURRENT_ACTION_TYPE);
}

function applyCampaign(campaign) {
  CAMPAIGN = campaign;
  applyLiveSnapshot(campaign.live || {});
  connectLiveEvents();
  if (CHARACTER_SHEET && !(campaign.character_sheet_slots || []).includes(CHARACTER_SHEET.slot_id)) {
    closeCharacterDrawer();
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
  CURRENT_ACTION_TYPE = mode;
  document.querySelectorAll(".action-mode").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  el("turn-input").placeholder = ACTION_MODE_CONFIG[mode].placeholder;
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

async function unclaimCurrentSlot() {
  const slot = claimedSlotId();
  if (!slot) return;
  try {
    const data = await api(`/api/campaigns/${SESSION.campaignId}/slots/${slot}/unclaim`, { method: "POST" });
    applyCampaign(data.campaign);
    showFlash(`Claim für ${slot.toUpperCase()} gelöst.`);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function submitTurn() {
  if (IS_SENDING_TURN) return;
  const actor = claimedSlotId();
  const content = el("turn-input").value.trim();
  if (!actor || !content) return;
  IS_SENDING_TURN = true;
  setBusy("submitTurnBtn", true, "Sende...");
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor, action_type: CURRENT_ACTION_TYPE, content })
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

async function continueStory() {
  if (IS_SENDING_TURN) return;
  const actor = claimedSlotId();
  if (!actor || !campaignHasIntro()) return;
  const lastTurn = (CAMPAIGN?.active_turns || []).slice(-1)[0];
  const lastBeat = (lastTurn?.gm_text_display || "").trim();
  IS_SENDING_TURN = true;
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor,
        action_type: "story",
        content: lastBeat
          ? `Weiter. Setze exakt bei diesem letzten Beat an: "${lastBeat}". Führe die aktuelle Szene organisch und ohne harten Sprung fort. Bleib bei den direkten Konsequenzen dieses Moments.`
          : "Weiter. Führe die aktuelle Szene organisch und ohne harten Sprung fort. Bleib bei den direkten Konsequenzen des letzten Turns."
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
  if (!SESSION.campaignId || !isHost()) return;
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
  if (!EDIT_TURN_ID) return;
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
  if (!confirm("Diesen Turn ab seinem Vorzustand neu ausrollen?")) return;
  try {
    clearPresenceActivity();
    const data = await api(`/api/campaigns/${SESSION.campaignId}/turns/${turnId}/retry`, { method: "POST" });
    applyCampaign(data.campaign);
    showFlash("Turn wurde neu gerollt.");
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
  if (target.id === "savePlotBtn") savePlotEssentials();
  if (target.id === "saveAuthorsNoteBtn") saveAuthorsNote();
  if (target.id === "saveStoryCardBtn") saveStoryCard();
  if (target.id === "saveWorldInfoBtn") saveWorldInfo();
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
  if (target.matches(".settings-tab")) setActiveSettingsTab(target.dataset.tab);
  if (target.matches(".drawer-tab")) setDrawerTab(target.dataset.drawerTab);
  if (target.dataset.action === "set-theme") setTheme(target.dataset.theme);
  if (target.dataset.action === "reroll-preview-answer") rerollSetupPreviewAnswer(target.dataset.index);
  if (target.dataset.action === "claim-slot") claimSlot(target.dataset.slotId);
  if (target.dataset.action === "open-character-sheet") openCharacterDrawer(target.dataset.slotId).catch((error) => showFlash(error.message, true));
  if (target.dataset.action === "edit-turn") openEditModal(target.dataset.turnId);
  if (target.dataset.action === "undo-turn") undoTurn(target.dataset.turnId);
  if (target.dataset.action === "retry-turn") retryTurn(target.dataset.turnId);
  if (target.dataset.action === "continue-turn") continueStory();
  if (target.dataset.action === "open-session") openSavedSession(target.dataset.campaignId);
  if (target.dataset.action === "edit-session") openSessionModal(target.dataset.campaignId);
  if (target.dataset.action === "forget-session") forgetSession(target.dataset.campaignId);
  if (target.dataset.action === "edit-story-card") {
    EDITING_STORY_CARD_ID = target.dataset.cardId;
    renderStoryCardsTab();
  }
  if (target.dataset.action === "edit-world-entry") {
    EDITING_WORLD_INFO_ID = target.dataset.entryId;
    renderWorldInfoTab();
  }
  if (target.id === "character-drawer") closeCharacterDrawer();
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
    if (String(target.id || "").startsWith("setup-answer") || target.classList?.contains("setup-answer-multi")) {
      scheduleSetupPresence();
    }
  }
});

document.addEventListener("change", (event) => {
  const target = event.target;
  if (!target) return;
  if (!el("setup-modal").classList.contains("hidden")) {
    if (String(target.id || "").startsWith("setup-answer") || target.classList?.contains("setup-answer-multi") || target.name === "setup-boolean") {
      scheduleSetupPresence();
    }
  }
});

bootstrap();

async function bootstrap() {
  applyTheme(CURRENT_THEME);
  setActiveSidebarTab("chars");
  setActiveSettingsTab("session");
  setActionMode("do");
  if (SESSION.campaignId && SESSION.playerId && SESSION.playerToken) {
    await loadCampaign();
    return;
  }
  renderLanding();
}

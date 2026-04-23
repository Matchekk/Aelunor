import type { SessionLibraryEntry } from "../../shared/api/contracts";

const SESSION_LIBRARY_KEY = "isekaiSessionLibrary";
const MAX_LIBRARY_ENTRIES = 25;

interface LegacySessionLibraryEntry {
  campaignId?: unknown;
  playerId?: unknown;
  playerToken?: unknown;
  joinCode?: unknown;
  title?: unknown;
  campaignTitle?: unknown;
  displayName?: unknown;
  lastUsedAt?: unknown;
}

export interface SessionLibraryUpsertInput {
  campaign_id: string;
  player_id: string;
  player_token: string;
  join_code: string;
  label?: string;
  campaign_title?: string | null;
  display_name?: string | null;
}

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function normalizeString(value: unknown): string {
  return String(value ?? "").trim();
}

function normalizeJoinCode(value: unknown): string {
  return normalizeString(value).toUpperCase().replace(/\s+/g, "");
}

function normalizeNullableString(value: unknown): string | null {
  const normalized = normalizeString(value);
  return normalized.length > 0 ? normalized : null;
}

function normalizeTimestamp(value: unknown): string {
  const normalized = normalizeString(value);
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? new Date(parsed).toISOString() : new Date().toISOString();
}

function defaultLabel(campaign_id: string): string {
  return `Session ${campaign_id.slice(0, 8)}`;
}

function asSessionLibraryEntry(raw: unknown): SessionLibraryEntry | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }

  const item = raw as Record<string, unknown>;
  const legacy = raw as LegacySessionLibraryEntry;

  const campaign_id = normalizeString(item.campaign_id ?? legacy.campaignId);
  const player_id = normalizeString(item.player_id ?? legacy.playerId);
  const player_token = normalizeString(item.player_token ?? legacy.playerToken);
  const join_code = normalizeJoinCode(item.join_code ?? legacy.joinCode);

  if (!campaign_id || !player_id || !player_token) {
    return null;
  }

  const label_source = item.label ?? item.campaign_title ?? legacy.title ?? defaultLabel(campaign_id);
  const label = normalizeString(label_source) || defaultLabel(campaign_id);
  const campaign_title = normalizeNullableString(item.campaign_title ?? legacy.campaignTitle ?? legacy.title);
  const display_name = normalizeNullableString(item.display_name ?? legacy.displayName);
  const updated_at = normalizeTimestamp(item.updated_at ?? legacy.lastUsedAt);

  return {
    campaign_id,
    player_id,
    player_token,
    join_code,
    label,
    updated_at,
    campaign_title,
    display_name,
  };
}

interface PersistedSessionLibraryEntry {
  campaignId: string;
  playerId: string;
  playerToken: string;
  joinCode: string;
  title: string;
  campaignTitle: string;
  displayName: string;
  lastUsedAt: string;
}

function toPersistedEntry(entry: SessionLibraryEntry): PersistedSessionLibraryEntry {
  return {
    campaignId: entry.campaign_id,
    playerId: entry.player_id,
    playerToken: entry.player_token,
    joinCode: entry.join_code,
    title: entry.label,
    campaignTitle: entry.campaign_title ?? "",
    displayName: entry.display_name ?? "",
    lastUsedAt: entry.updated_at,
  };
}

function saveSessionLibrary(entries: SessionLibraryEntry[]): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  try {
    storage.setItem(
      SESSION_LIBRARY_KEY,
      JSON.stringify(entries.slice(0, MAX_LIBRARY_ENTRIES).map((entry) => toPersistedEntry(entry))),
    );
  } catch {
    // Local session history is a convenience feature. Never block the app if storage is unavailable or full.
  }
}

function clearCorruptSessionLibrary(): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  try {
    storage.removeItem(SESSION_LIBRARY_KEY);
  } catch {
    // Ignore storage failures during recovery.
  }
}

export function normalizeSessionLibraryEntries(parsed: unknown): SessionLibraryEntry[] {
  if (!Array.isArray(parsed)) {
    return [];
  }

  const deduped = new Map<string, SessionLibraryEntry>();
  for (const item of parsed) {
    const entry = asSessionLibraryEntry(item);
    if (!entry) {
      continue;
    }
    const existing = deduped.get(entry.campaign_id);
    if (!existing || existing.updated_at.localeCompare(entry.updated_at) < 0) {
      deduped.set(entry.campaign_id, entry);
    }
  }

  return Array.from(deduped.values())
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, MAX_LIBRARY_ENTRIES);
}

export function readSessionLibrary(): SessionLibraryEntry[] {
  const storage = getStorage();
  if (!storage) {
    return [];
  }

  let parsed: unknown = [];
  let shouldHeal = false;
  try {
    const raw = storage.getItem(SESSION_LIBRARY_KEY);
    parsed = raw ? JSON.parse(raw) : [];
    shouldHeal = raw !== null;
  } catch (_error) {
    clearCorruptSessionLibrary();
    return [];
  }

  const entries = normalizeSessionLibraryEntries(parsed);

  // Heal malformed legacy payloads, invalid rows, duplicates, non-array payloads and overlong lists.
  if (shouldHeal) {
    saveSessionLibrary(entries);
  }

  return entries;
}

export function upsertSessionLibraryEntry(input: SessionLibraryUpsertInput): SessionLibraryEntry {
  const entries = readSessionLibrary();
  const now = new Date().toISOString();

  const campaign_id = normalizeString(input.campaign_id);
  const player_id = normalizeString(input.player_id);
  const player_token = normalizeString(input.player_token);

  if (!campaign_id || !player_id || !player_token) {
    throw new Error("Cannot store incomplete session credentials.");
  }

  const nextEntry: SessionLibraryEntry = {
    campaign_id,
    player_id,
    player_token,
    join_code: normalizeJoinCode(input.join_code),
    label: normalizeString(input.label) || defaultLabel(campaign_id),
    updated_at: now,
    campaign_title: normalizeNullableString(input.campaign_title),
    display_name: normalizeNullableString(input.display_name),
  };

  const filtered = entries.filter((entry) => entry.campaign_id !== nextEntry.campaign_id);
  const nextEntries = [nextEntry, ...filtered].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  saveSessionLibrary(nextEntries);
  return nextEntry;
}

export function forgetSessionLibraryEntry(campaign_id: string): void {
  const normalized = normalizeString(campaign_id);
  if (!normalized) {
    return;
  }
  const nextEntries = readSessionLibrary().filter((entry) => entry.campaign_id !== normalized);
  saveSessionLibrary(nextEntries);
}

export function renameSessionLibraryEntry(campaign_id: string, label: string): SessionLibraryEntry | null {
  const normalizedCampaignId = normalizeString(campaign_id);
  const normalizedLabel = normalizeString(label);
  if (!normalizedCampaignId || !normalizedLabel) {
    return null;
  }

  const entries = readSessionLibrary();
  let nextEntry: SessionLibraryEntry | null = null;
  const now = new Date().toISOString();
  const nextEntries = entries.map((entry) => {
    if (entry.campaign_id !== normalizedCampaignId) {
      return entry;
    }
    nextEntry = {
      ...entry,
      label: normalizedLabel,
      updated_at: now,
    };
    return nextEntry;
  });

  saveSessionLibrary(nextEntries);
  return nextEntry;
}

export function deleteSessionLibraryEntry(campaign_id: string): void {
  forgetSessionLibraryEntry(campaign_id);
}

export function exportSessionLibraryEntry(campaign_id: string): Record<string, unknown> | null {
  const normalizedCampaignId = normalizeString(campaign_id);
  if (!normalizedCampaignId) {
    return null;
  }
  const entry = readSessionLibrary().find((item) => item.campaign_id === normalizedCampaignId);
  if (!entry) {
    return null;
  }
  return {
    campaign_id: entry.campaign_id,
    player_id: entry.player_id,
    player_token: entry.player_token,
    join_code: entry.join_code,
    label: entry.label,
    campaign_title: entry.campaign_title ?? null,
    display_name: entry.display_name ?? null,
    updated_at: entry.updated_at,
    exported_at: new Date().toISOString(),
  };
}

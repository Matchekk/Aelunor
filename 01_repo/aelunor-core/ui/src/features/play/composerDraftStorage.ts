import type { PlayModeId } from "./modeConfig";
import { PLAY_MODE_CONFIG } from "./modeConfig";

const STORAGE_PREFIX = "aelunorComposerDraftsV1:";
const MAX_DRAFT_LENGTH = 6000;

type DraftMap = Record<PlayModeId, string>;

function emptyDrafts(): DraftMap {
  return PLAY_MODE_CONFIG.reduce<DraftMap>((acc, mode) => {
    acc[mode.id] = "";
    return acc;
  }, {} as DraftMap);
}

function storageKey(scope: string): string {
  return `${STORAGE_PREFIX}${encodeURIComponent(scope)}`;
}

function localStorageSafe(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function sanitizeDrafts(value: unknown): DraftMap {
  const raw = readRecord(value);
  const next = emptyDrafts();
  for (const mode of PLAY_MODE_CONFIG) {
    const draft = raw[mode.id];
    next[mode.id] = typeof draft === "string" ? draft.slice(0, MAX_DRAFT_LENGTH) : "";
  }
  return next;
}

function hasAnyDraft(drafts: DraftMap): boolean {
  return Object.values(drafts).some((value) => value.trim().length > 0);
}

export function buildComposerDraftScope(campaign_id: string, actor_id: string | null | undefined, player_id: string | null | undefined): string {
  const campaignPart = String(campaign_id || "unknown-campaign").trim() || "unknown-campaign";
  const actorPart = String(actor_id || "").trim();
  const playerPart = String(player_id || "").trim();
  return `${campaignPart}:${actorPart || `viewer:${playerPart || "anonymous"}`}`;
}

export function readComposerDrafts(scope: string): DraftMap {
  const storage = localStorageSafe();
  if (!storage) {
    return emptyDrafts();
  }

  const raw = storage.getItem(storageKey(scope));
  if (!raw) {
    return emptyDrafts();
  }

  try {
    return sanitizeDrafts(JSON.parse(raw) as unknown);
  } catch {
    storage.removeItem(storageKey(scope));
    return emptyDrafts();
  }
}

export function writeComposerDrafts(scope: string, drafts: DraftMap): void {
  const storage = localStorageSafe();
  if (!storage) {
    return;
  }

  const sanitized = sanitizeDrafts(drafts);
  const key = storageKey(scope);

  try {
    if (!hasAnyDraft(sanitized)) {
      storage.removeItem(key);
      return;
    }
    storage.setItem(key, JSON.stringify(sanitized));
  } catch {
    // Draft persistence is a comfort feature. Never block the composer if localStorage is full or unavailable.
  }
}

export function clearComposerDrafts(scope: string): void {
  const storage = localStorageSafe();
  if (!storage) {
    return;
  }
  storage.removeItem(storageKey(scope));
}

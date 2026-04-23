const SESSION_KEYS = {
  campaign_id: "isekaiCampaignId",
  player_id: "isekaiPlayerId",
  player_token: "isekaiPlayerToken",
  join_code: "isekaiJoinCode",
} as const;

export interface SessionBootstrap {
  campaign_id: string | null;
  player_id: string | null;
  player_token: string | null;
  join_code: string | null;
}

const EMPTY_SESSION_BOOTSTRAP: SessionBootstrap = {
  campaign_id: null,
  player_id: null,
  player_token: null,
  join_code: null,
};

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

function normalizeNullable(value: string | null | undefined): string | null {
  const normalized = String(value ?? "").trim();
  return normalized.length > 0 ? normalized : null;
}

function normalizeJoinCode(value: string | null | undefined): string | null {
  const normalized = normalizeNullable(value);
  return normalized ? normalized.toUpperCase().replace(/\s+/g, "") : null;
}

function normalizeBootstrap(raw: Partial<SessionBootstrap>): SessionBootstrap {
  return {
    campaign_id: normalizeNullable(raw.campaign_id),
    player_id: normalizeNullable(raw.player_id),
    player_token: normalizeNullable(raw.player_token),
    join_code: normalizeJoinCode(raw.join_code),
  };
}

function hasCompleteCredentials(session: SessionBootstrap): boolean {
  return Boolean(session.campaign_id && session.player_id && session.player_token);
}

function hasPartialCredentials(session: SessionBootstrap): boolean {
  return Boolean(session.campaign_id || session.player_id || session.player_token);
}

function persistSessionBootstrap(storage: Storage, session: SessionBootstrap): void {
  const entries: Array<[keyof SessionBootstrap, string]> = [
    ["campaign_id", SESSION_KEYS.campaign_id],
    ["player_id", SESSION_KEYS.player_id],
    ["player_token", SESSION_KEYS.player_token],
    ["join_code", SESSION_KEYS.join_code],
  ];

  try {
    for (const [stateKey, storageKey] of entries) {
      const value = stateKey === "join_code" ? normalizeJoinCode(session[stateKey]) : normalizeNullable(session[stateKey]);
      if (value) {
        storage.setItem(storageKey, value);
      } else {
        storage.removeItem(storageKey);
      }
    }
  } catch {
    // Storage persistence must never break initial app boot.
  }
}

export function readSessionBootstrap(): SessionBootstrap {
  const storage = getStorage();
  if (!storage) {
    return { ...EMPTY_SESSION_BOOTSTRAP };
  }

  const raw = normalizeBootstrap({
    campaign_id: storage.getItem(SESSION_KEYS.campaign_id),
    player_id: storage.getItem(SESSION_KEYS.player_id),
    player_token: storage.getItem(SESSION_KEYS.player_token),
    join_code: storage.getItem(SESSION_KEYS.join_code),
  });

  if (hasPartialCredentials(raw) && !hasCompleteCredentials(raw)) {
    persistSessionBootstrap(storage, EMPTY_SESSION_BOOTSTRAP);
    return { ...EMPTY_SESSION_BOOTSTRAP };
  }

  persistSessionBootstrap(storage, raw);
  return raw;
}

export function writeSessionBootstrap(patch: Partial<SessionBootstrap>): SessionBootstrap {
  const storage = getStorage();
  const next = normalizeBootstrap({ ...readSessionBootstrap(), ...patch });

  if (hasPartialCredentials(next) && !hasCompleteCredentials(next)) {
    if (storage) {
      persistSessionBootstrap(storage, EMPTY_SESSION_BOOTSTRAP);
    }
    return { ...EMPTY_SESSION_BOOTSTRAP };
  }

  if (!storage) {
    return next;
  }

  persistSessionBootstrap(storage, next);
  return next;
}

export function clearSessionBootstrap(): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  persistSessionBootstrap(storage, EMPTY_SESSION_BOOTSTRAP);
}

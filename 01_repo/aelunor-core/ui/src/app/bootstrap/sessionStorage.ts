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

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function normalizeNullable(value: string | null): string | null {
  const normalized = String(value ?? "").trim();
  return normalized.length > 0 ? normalized : null;
}

export function readSessionBootstrap(): SessionBootstrap {
  const storage = getStorage();
  if (!storage) {
    return {
      campaign_id: null,
      player_id: null,
      player_token: null,
      join_code: null,
    };
  }
  return {
    campaign_id: normalizeNullable(storage.getItem(SESSION_KEYS.campaign_id)),
    player_id: normalizeNullable(storage.getItem(SESSION_KEYS.player_id)),
    player_token: normalizeNullable(storage.getItem(SESSION_KEYS.player_token)),
    join_code: normalizeNullable(storage.getItem(SESSION_KEYS.join_code)),
  };
}

export function writeSessionBootstrap(patch: Partial<SessionBootstrap>): SessionBootstrap {
  const storage = getStorage();
  const next = { ...readSessionBootstrap(), ...patch };
  if (!storage) {
    return next;
  }

  const entries: Array<[keyof SessionBootstrap, string]> = [
    ["campaign_id", SESSION_KEYS.campaign_id],
    ["player_id", SESSION_KEYS.player_id],
    ["player_token", SESSION_KEYS.player_token],
    ["join_code", SESSION_KEYS.join_code],
  ];

  for (const [stateKey, storageKey] of entries) {
    const value = normalizeNullable(next[stateKey]);
    if (value) {
      storage.setItem(storageKey, value);
    } else {
      storage.removeItem(storageKey);
    }
  }

  return next;
}

export function clearSessionBootstrap(): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.removeItem(SESSION_KEYS.campaign_id);
  storage.removeItem(SESSION_KEYS.player_id);
  storage.removeItem(SESSION_KEYS.player_token);
  storage.removeItem(SESSION_KEYS.join_code);
}

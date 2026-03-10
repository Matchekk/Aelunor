import type { ContextQueryResponse } from "../../shared/api/contracts";

const CONTEXT_CACHE_KEY = "aelunorV1ContextCache";

type ContextCacheRecord = Record<string, ContextQueryResponse>;

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage;
}

function readCache(): ContextCacheRecord {
  const storage = getStorage();
  if (!storage) {
    return {};
  }

  const raw = storage.getItem(CONTEXT_CACHE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as ContextCacheRecord) : {};
  } catch {
    return {};
  }
}

function writeCache(cache: ContextCacheRecord): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.setItem(CONTEXT_CACHE_KEY, JSON.stringify(cache));
}

export function writeContextCache(campaign_id: string, payload: ContextQueryResponse): void {
  const cache = readCache();
  cache[campaign_id] = payload;
  writeCache(cache);
}

export function readContextCache(campaign_id: string): ContextQueryResponse | null {
  return readCache()[campaign_id] ?? null;
}


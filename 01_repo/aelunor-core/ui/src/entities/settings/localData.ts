const SESSION_LIBRARY_KEY = "isekaiSessionLibrary";
const NOVELTY_KEY = "isekaiNoveltyState";
const PLAY_UI_MEMORY_KEY = "aelunorPlayUiMemoryV1";
const SETTINGS_UI_MEMORY_KEY = "aelunorSettingsUiMemoryV1";
const CONTEXT_CACHE_KEY = "aelunorV1ContextCache";

function localStorageSafe(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function sessionStorageSafe(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage;
}

export function clearLocalComfortData(): void {
  clearLocalComfortDataFromStorages(localStorageSafe(), sessionStorageSafe());
}

export function clearLocalComfortDataFromStorages(local: Storage | null, session: Storage | null): void {
  if (local) {
    local.removeItem(SESSION_LIBRARY_KEY);
    local.removeItem(NOVELTY_KEY);
    local.removeItem(PLAY_UI_MEMORY_KEY);
    local.removeItem(SETTINGS_UI_MEMORY_KEY);
  }

  if (session) {
    session.removeItem(CONTEXT_CACHE_KEY);
  }
}

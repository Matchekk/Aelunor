const PLAY_UI_MEMORY_KEY = "aelunorPlayUiMemoryV1";

interface PlayUiMemoryEntry {
  scene_id: string | null;
  right_rail_open: boolean | null;
}

type PlayUiMemoryState = Record<string, PlayUiMemoryEntry>;

function localStorageSafe(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readState(): PlayUiMemoryState {
  const storage = localStorageSafe();
  if (!storage) {
    return {};
  }
  const raw = storage.getItem(PLAY_UI_MEMORY_KEY);
  if (!raw) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as PlayUiMemoryState) : {};
  } catch {
    return {};
  }
}

function writeState(state: PlayUiMemoryState): void {
  const storage = localStorageSafe();
  if (!storage) {
    return;
  }
  storage.setItem(PLAY_UI_MEMORY_KEY, JSON.stringify(state));
}

export function readPlayUiMemory(campaign_id: string): PlayUiMemoryEntry {
  const entry = readRecord(readState()[campaign_id]);
  const sceneRaw = typeof entry.scene_id === "string" ? entry.scene_id.trim() : "";
  const rightRailRaw = typeof entry.right_rail_open === "boolean" ? entry.right_rail_open : null;
  return {
    scene_id: sceneRaw.length > 0 ? sceneRaw : null,
    right_rail_open: rightRailRaw,
  };
}

export function writePlayUiMemory(
  campaign_id: string,
  patch: Partial<{ scene_id: string | null; right_rail_open: boolean | null }>,
): void {
  if (!campaign_id) {
    return;
  }
  const state = readState();
  const current = readPlayUiMemory(campaign_id);
  const scene = patch.scene_id === undefined ? current.scene_id : patch.scene_id;
  const rightRail = patch.right_rail_open === undefined ? current.right_rail_open : patch.right_rail_open;

  state[campaign_id] = {
    scene_id: scene,
    right_rail_open: rightRail,
  };
  writeState(state);
}

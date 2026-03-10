import type { CampaignSnapshot } from "../../shared/api/contracts";

const NOVELTY_STORAGE_KEY = "isekaiNoveltyState";

interface NoveltyBucket {
  items: Record<string, number>;
}

type NoveltyState = Record<string, NoveltyBucket>;

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function readState(): NoveltyState {
  const storage = getStorage();
  if (!storage) {
    return {};
  }

  try {
    const raw = storage.getItem(NOVELTY_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as NoveltyState) : {};
  } catch (_error) {
    return {};
  }
}

function writeState(state: NoveltyState): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.setItem(NOVELTY_STORAGE_KEY, JSON.stringify(state));
}

function noveltyBucket(campaign_id: string, create = false): NoveltyBucket | null {
  const state = readState();
  let bucket = state[campaign_id];
  if (!bucket && create) {
    bucket = { items: {} };
    state[campaign_id] = bucket;
    writeState(state);
  }
  return bucket ?? null;
}

function setBucket(campaign_id: string, bucket: NoveltyBucket): void {
  const state = readState();
  state[campaign_id] = bucket;
  writeState(state);
}

function addNovelty(campaign_id: string, key: string, amount = 1): boolean {
  if (!campaign_id || !key || amount <= 0) {
    return false;
  }
  const bucket = noveltyBucket(campaign_id, true);
  if (!bucket) {
    return false;
  }
  bucket.items[key] = Math.max(0, Number(bucket.items[key] || 0)) + amount;
  setBucket(campaign_id, bucket);
  return true;
}

function clearNovelty(campaign_id: string, key: string): boolean {
  const bucket = noveltyBucket(campaign_id, false);
  if (!bucket || !(key in bucket.items)) {
    return false;
  }
  delete bucket.items[key];
  setBucket(campaign_id, bucket);
  return true;
}

function countNovelty(campaign_id: string, key: string): number {
  const bucket = noveltyBucket(campaign_id, false);
  if (!bucket) {
    return 0;
  }
  const count = Number(bucket.items[key] || 0);
  return Number.isFinite(count) && count > 0 ? Math.floor(count) : 0;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function rankValue(rank: unknown): number {
  const value = String(rank || "F").trim().toUpperCase();
  return { F: 1, E: 2, D: 3, C: 4, B: 5, A: 6, S: 7 }[value as "F"] ?? 1;
}

function injuryIdentity(entry: unknown, index: number): string {
  const record = readRecord(entry);
  const primary = String(record.id || record.title || record.name || "").trim();
  if (primary) {
    return primary.toLowerCase();
  }
  return `${String(record.severity || "").trim()}|${String(record.healing_stage || "").trim()}|${index}`.toLowerCase();
}

export function trackCampaignNovelty(previousCampaign: CampaignSnapshot | null, nextCampaign: CampaignSnapshot): boolean {
  const campaign_id = nextCampaign.campaign_meta.campaign_id;
  if (!previousCampaign || previousCampaign.campaign_meta.campaign_id !== campaign_id) {
    return false;
  }

  let changed = false;
  const prevCharacters = readRecord(previousCampaign.state).characters;
  const nextCharacters = readRecord(nextCampaign.state).characters;

  Object.entries(readRecord(nextCharacters)).forEach(([slot_id, nextValue]) => {
    const prevCharacter = readRecord(readRecord(prevCharacters)[slot_id]);
    const nextCharacter = readRecord(nextValue);

    const prevSkills = readRecord(prevCharacter.skills);
    const nextSkills = readRecord(nextCharacter.skills);
    const newSkillCount = Object.keys(nextSkills).filter((skill_id) => !(skill_id in prevSkills)).length;
    if (newSkillCount > 0) {
      changed = addNovelty(campaign_id, `skill:${slot_id}`, newSkillCount) || changed;
    }

    const prevClass = readRecord(prevCharacter.class_current);
    const nextClass = readRecord(nextCharacter.class_current);
    if (Object.keys(nextClass).length > 0 && Object.keys(prevClass).length === 0) {
      changed = addNovelty(campaign_id, `class:${slot_id}`, 1) || changed;
    } else if (Object.keys(nextClass).length > 0) {
      const prevLevel = Number(prevClass.level || 1);
      const nextLevel = Number(nextClass.level || 1);
      if (nextLevel > prevLevel) {
        changed = addNovelty(campaign_id, `class:${slot_id}`, Math.floor(nextLevel - prevLevel)) || changed;
      }
      if (rankValue(nextClass.rank) > rankValue(prevClass.rank)) {
        changed = addNovelty(campaign_id, `class:${slot_id}`, 1) || changed;
      }
    }

    const prevInjuries = new Set(
      (Array.isArray(prevCharacter.injuries) ? prevCharacter.injuries : []).map((entry, index) => injuryIdentity(entry, index)),
    );
    const nextInjuries = (Array.isArray(nextCharacter.injuries) ? nextCharacter.injuries : []).map((entry, index) =>
      injuryIdentity(entry, index),
    );
    const newInjuryCount = nextInjuries.filter((injury_id) => !prevInjuries.has(injury_id)).length;
    if (newInjuryCount > 0) {
      changed = addNovelty(campaign_id, `injury:${slot_id}`, newInjuryCount) || changed;
    }
  });

  const prevCodex = readRecord(readRecord(previousCampaign.state).codex);
  const nextCodex = readRecord(readRecord(nextCampaign.state).codex);
  const prevRaces = readRecord(prevCodex.races);
  const nextRaces = readRecord(nextCodex.races);
  Object.entries(nextRaces).forEach(([race_id, nextEntry]) => {
    const prevLevel = Number(readRecord(prevRaces[race_id]).knowledge_level || 0);
    const nextLevel = Number(readRecord(nextEntry).knowledge_level || 0);
    if (nextLevel > prevLevel) {
      changed = addNovelty(campaign_id, `codex:race:${race_id}`, Math.floor(nextLevel - prevLevel)) || changed;
    }
  });

  const prevBeasts = readRecord(prevCodex.beasts);
  const nextBeasts = readRecord(nextCodex.beasts);
  Object.entries(nextBeasts).forEach(([beast_id, nextEntry]) => {
    const prevLevel = Number(readRecord(prevBeasts[beast_id]).knowledge_level || 0);
    const nextLevel = Number(readRecord(nextEntry).knowledge_level || 0);
    if (nextLevel > prevLevel) {
      changed = addNovelty(campaign_id, `codex:beast:${beast_id}`, Math.floor(nextLevel - prevLevel)) || changed;
    }
    if (prevLevel <= 0 && nextLevel > 0) {
      changed = addNovelty(campaign_id, `beast:new:${beast_id}`, 1) || changed;
    }
  });

  if (previousCampaign.boards.memory_summary.updated_through_turn < nextCampaign.boards.memory_summary.updated_through_turn) {
    changed = addNovelty(campaign_id, "board:memory", 1) || changed;
  }
  if (previousCampaign.boards.plot_essentials.updated_at !== nextCampaign.boards.plot_essentials.updated_at) {
    changed = addNovelty(campaign_id, "board:plot", 1) || changed;
  }
  if (previousCampaign.boards.authors_note.updated_at !== nextCampaign.boards.authors_note.updated_at) {
    changed = addNovelty(campaign_id, "board:note", 1) || changed;
  }
  if (previousCampaign.boards.story_cards.length !== nextCampaign.boards.story_cards.length) {
    changed = addNovelty(campaign_id, "board:cards", 1) || changed;
  }
  if (previousCampaign.boards.world_info.length !== nextCampaign.boards.world_info.length) {
    changed = addNovelty(campaign_id, "board:world", 1) || changed;
  }

  return changed;
}

export function getNoveltyCount(campaign_id: string, key: string): number {
  return countNovelty(campaign_id, key);
}

export function getNoveltyCountByPrefix(campaign_id: string, prefix: string): number {
  const bucket = noveltyBucket(campaign_id, false);
  if (!bucket) {
    return 0;
  }
  return Object.entries(bucket.items).reduce((total, [key, count]) => {
    if (!key.startsWith(prefix)) {
      return total;
    }
    const numeric = Number(count || 0);
    return total + (Number.isFinite(numeric) && numeric > 0 ? Math.floor(numeric) : 0);
  }, 0);
}

export function clearCharacterNovelty(campaign_id: string, slot_id: string, tab_id = "overview"): boolean {
  const keys =
    tab_id === "skills"
      ? [`skill:${slot_id}`]
      : tab_id === "class"
        ? [`class:${slot_id}`]
        : tab_id === "injuries"
          ? [`injury:${slot_id}`]
          : [`skill:${slot_id}`, `class:${slot_id}`, `injury:${slot_id}`];
  return keys.some((key) => clearNovelty(campaign_id, key));
}

export function clearCodexNovelty(campaign_id: string, kind: "race" | "beast", entity_id: string): boolean {
  const keys = kind === "beast" ? [`codex:beast:${entity_id}`, `beast:new:${entity_id}`] : [`codex:race:${entity_id}`];
  return keys.some((key) => clearNovelty(campaign_id, key));
}

export function clearBoardNovelty(campaign_id: string, tab_id: "plot" | "note" | "cards" | "world" | "memory" | "session"): boolean {
  const keyMap = {
    plot: "board:plot",
    note: "board:note",
    cards: "board:cards",
    world: "board:world",
    memory: "board:memory",
    session: "board:session",
  } as const;
  return clearNovelty(campaign_id, keyMap[tab_id]);
}

export function deriveBoardNoveltyCount(campaign_id: string): number {
  return ["board:plot", "board:note", "board:cards", "board:world", "board:memory", "board:session"].reduce(
    (total, key) => total + getNoveltyCount(campaign_id, key),
    0,
  );
}

export function noveltyLabel(count: number): string | null {
  if (count <= 0) {
    return null;
  }
  return count > 1 ? `+${count}` : "New";
}

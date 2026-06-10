import type {
  CampaignSnapshot,
  CampaignTurn,
  DisplayPartyEntry,
  PartyOverviewEntry,
} from "../../shared/api/contracts";

export interface UiResourceValue {
  current: number | null;
  max: number | null;
  text: string;
  percent: number | null;
}

export interface UiCharacterSummary {
  slot_id: string;
  name: string;
  class_label: string;
  level_label: string;
  hp: UiResourceValue;
  stamina: UiResourceValue;
  resource: UiResourceValue;
  resource_name: string;
  karma_label: string;
  conditions: string[];
  scene_label: string;
  in_combat: boolean;
  injury_count: number;
  is_viewer: boolean;
}

export interface UiSceneSummary {
  label: string;
  time_label: string;
  weather_label: string;
}

export interface UiPartyHudState {
  characters: UiCharacterSummary[];
  scene: UiSceneSummary;
  party_count: number;
  phase_label: string;
  viewer_slot_id: string | null;
}

export const FALLBACK_NAME = "Unbenannte Figur";
export const FALLBACK_CLASS = "Unbekannte Klasse";
export const FALLBACK_SCENE = "Unbekannter Ort";
export const FALLBACK_KARMA = "Neutral";
export const FALLBACK_RESOURCE_TEXT = "—";

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

// Fresh / not yet normalized campaign snapshots can miss whole top-level
// fields; components must read arrays and nested records only through these.
export function partyOverview(campaign: CampaignSnapshot): PartyOverviewEntry[] {
  return readArray<PartyOverviewEntry>(campaign.party_overview);
}

export function displayParty(campaign: CampaignSnapshot): DisplayPartyEntry[] {
  return readArray<DisplayPartyEntry>(campaign.display_party);
}

export function activeTurns(campaign: CampaignSnapshot): CampaignTurn[] {
  return readArray<CampaignTurn>(campaign.active_turns);
}

export function characterSheetSlots(campaign: CampaignSnapshot): string[] {
  return readArray<unknown>(campaign.character_sheet_slots).filter(
    (entry): entry is string => typeof entry === "string",
  );
}

export function viewerContext(campaign: CampaignSnapshot): Record<string, unknown> {
  return readRecord(campaign.viewer_context);
}

export function viewerClaimedSlotId(campaign: CampaignSnapshot): string | null {
  return readString(viewerContext(campaign).claimed_slot_id) || null;
}

export function plotEssentials(campaign: CampaignSnapshot): Record<string, unknown> {
  return readRecord(readRecord(campaign.boards).plot_essentials);
}

export function worldTime(campaign: CampaignSnapshot): Record<string, unknown> {
  return readRecord(campaign.world_time);
}

function readString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function firstString(...values: unknown[]): string {
  for (const value of values) {
    const text = readString(value);
    if (text) {
      return text;
    }
  }
  return "";
}

function characterState(campaign: CampaignSnapshot, slot_id: string): Record<string, unknown> {
  return readRecord(readRecord(readRecord(campaign.state).characters)[slot_id]);
}

export function formatResourceValue(current: unknown, max: unknown): UiResourceValue {
  const maxValue = readNumber(max);
  if (maxValue === null || maxValue <= 0) {
    return { current: null, max: null, text: FALLBACK_RESOURCE_TEXT, percent: null };
  }
  const rawCurrent = readNumber(current) ?? 0;
  const clamped = Math.max(0, Math.min(maxValue, rawCurrent));
  return {
    current: clamped,
    max: maxValue,
    text: `${clamped}/${maxValue}`,
    percent: Math.max(0, Math.min(100, Math.round((clamped / maxValue) * 100))),
  };
}

function reputationEntryLabel(entry: unknown): string {
  if (typeof entry === "string") {
    return entry.trim();
  }
  const record = readRecord(entry);
  const target = firstString(record.name, record.faction, record.group, record.target, record.region);
  const standing = firstString(record.standing, record.attitude, record.label, record.status, record.value);
  if (target && standing) {
    return `${target}: ${standing}`;
  }
  return target || standing;
}

export function deriveKarmaLabel(campaign: CampaignSnapshot, slot_id: string): string {
  const journal = readRecord(characterState(campaign, slot_id).journal);
  const labels = readArray(journal.reputation)
    .map(reputationEntryLabel)
    .filter(Boolean)
    .slice(0, 2);
  return labels.length > 0 ? labels.join(" · ") : FALLBACK_KARMA;
}

export function resolveSceneLabel(campaign: CampaignSnapshot, scene_id: unknown, scene_name: unknown): string {
  const directName = readString(scene_name);
  if (directName) {
    return directName;
  }
  const sceneId = readString(scene_id);
  if (!sceneId) {
    return FALLBACK_SCENE;
  }
  const state = readRecord(campaign.state);
  const fromScenes = readString(readRecord(readRecord(state.scenes)[sceneId]).name);
  if (fromScenes) {
    return fromScenes;
  }
  const fromMap = readString(readRecord(readRecord(readRecord(state.map).nodes)[sceneId]).name);
  return fromMap || sceneId;
}

function classLabel(entry: PartyOverviewEntry): string {
  const name = readString(entry.class_name);
  const rank = readString(entry.class_rank);
  if (!name) {
    return FALLBACK_CLASS;
  }
  return rank ? `${name} · Rang ${rank}` : name;
}

function levelLabel(entry: PartyOverviewEntry): string {
  const level = readNumber(entry.class_level) ?? readNumber(entry.level);
  return level !== null ? `Lv ${level}` : "";
}

export function deriveCharacterSummary(campaign: CampaignSnapshot, entry: PartyOverviewEntry): UiCharacterSummary {
  const bio = readRecord(characterState(campaign, entry.slot_id).bio);
  return {
    slot_id: entry.slot_id,
    name: firstString(entry.display_name, bio.name) || FALLBACK_NAME,
    class_label: classLabel(entry),
    level_label: levelLabel(entry),
    hp: formatResourceValue(entry.hp_current, entry.hp_max),
    stamina: formatResourceValue(entry.sta_current, entry.sta_max),
    resource: formatResourceValue(entry.res_current, entry.res_max),
    resource_name: readString(entry.resource_name) || "Ressource",
    karma_label: deriveKarmaLabel(campaign, entry.slot_id),
    conditions: (entry.conditions ?? []).map(readString).filter(Boolean).slice(0, 3),
    scene_label: resolveSceneLabel(campaign, entry.scene_id, entry.scene_name),
    in_combat: entry.in_combat === true,
    injury_count: readNumber(entry.injury_count) ?? 0,
    is_viewer: viewerClaimedSlotId(campaign) === entry.slot_id,
  };
}

function deriveSceneSummary(campaign: CampaignSnapshot): UiSceneSummary {
  const party = partyOverview(campaign);
  const activeScene = readString(plotEssentials(campaign).active_scene);
  const viewerSlot = viewerClaimedSlotId(campaign);
  const viewerEntry = viewerSlot ? party.find((entry) => entry.slot_id === viewerSlot) : undefined;
  const fallbackEntry = viewerEntry ?? party[0];
  const label = activeScene || (fallbackEntry ? resolveSceneLabel(campaign, fallbackEntry.scene_id, fallbackEntry.scene_name) : FALLBACK_SCENE);
  return {
    label,
    time_label: readString(worldTime(campaign).time_of_day) || "Zeit unbekannt",
    weather_label: readString(worldTime(campaign).weather) || "Wetter unbekannt",
  };
}

export function derivePartyHud(campaign: CampaignSnapshot): UiPartyHudState {
  const party = partyOverview(campaign);
  const meta = readRecord(readRecord(campaign.state).meta);
  return {
    characters: party.map((entry) => deriveCharacterSummary(campaign, entry)),
    scene: deriveSceneSummary(campaign),
    party_count: party.length,
    phase_label:
      firstString(
        readRecord(campaign.setup_runtime).phase_display,
        meta.phase,
        viewerContext(campaign).phase,
        readRecord(campaign.campaign_meta).status,
      ) || "Unbekannte Phase",
    viewer_slot_id: viewerClaimedSlotId(campaign),
  };
}

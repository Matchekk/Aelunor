import type { CampaignSnapshot, CharacterSheetResponse, PartyOverviewEntry } from "../../shared/api/contracts";
import {
  characterSheetSlots,
  deriveKarmaLabel,
  partyOverview,
  resolveSceneLabel,
  viewerClaimedSlotId,
  FALLBACK_NAME,
} from "./partyHudModel";

export type ActorPanelSection =
  | "overview"
  | "resources"
  | "status"
  | "body"
  | "skills"
  | "equipment"
  | "inventory"
  | "bonds";

export interface ResourceMeter {
  key: string;
  label: string;
  current: number | null;
  max: number | null;
  tone: "hp" | "stamina" | "essence";
}

export interface ActorDockView {
  slot_id: string;
  display_name: string;
  species: string;
  class_name: string;
  class_rank: string;
  level: number | null;
  xp_current: number | null;
  xp_to_next: number | null;
  active: boolean;
  karma_label: string;
  scene_label: string;
  resources: ResourceMeter[];
  conditions: string[];
  injury_count: number;
  scar_count: number;
  effects_count: number;
  can_act_label: string;
  body_energy: string;
  body_pain: string;
  pressure: string;
  skills: Array<{ id: string; name: string; value: string; class_match: boolean }>;
  equipment: Array<{ slot: string; name: string }>;
  items: Array<{ id: string; name: string }>;
  bonds: Array<{ id: string; name: string; detail: string }>;
  factions: string[];
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function readString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function titleize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
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

function livingProfile(campaign: CampaignSnapshot, slot_id: string): Record<string, unknown> {
  return readRecord(characterState(campaign, slot_id).living_profile);
}

function asFallbackPartyEntry(campaign: CampaignSnapshot, slot_id: string | null): PartyOverviewEntry | null {
  const party = partyOverview(campaign);
  if (!slot_id) {
    return party[0] ?? null;
  }
  return party.find((entry) => entry.slot_id === slot_id) ?? null;
}

export function resolveSelectedActorId(campaign: CampaignSnapshot, selected_slot_id: string | null): string | null {
  const sheetSlots = characterSheetSlots(campaign);
  if (selected_slot_id && sheetSlots.includes(selected_slot_id)) {
    return selected_slot_id;
  }
  const claimed = viewerClaimedSlotId(campaign);
  if (claimed && sheetSlots.includes(claimed)) {
    return claimed;
  }
  return partyOverview(campaign)[0]?.slot_id ?? sheetSlots[0] ?? null;
}

function resourceMeters(sheet: CharacterSheetResponse | null, party: PartyOverviewEntry | null): ResourceMeter[] {
  const resources = sheet?.sheet.overview.resources;
  const resourceName = firstString(sheet?.sheet.overview.resource_label, resources?.resource_name, party?.resource_name) || "Essenz";
  return [
    {
      key: "hp",
      label: "Leben",
      current: readNumber(resources?.hp_current) ?? readNumber(party?.hp_current),
      max: readNumber(resources?.hp_max) ?? readNumber(party?.hp_max),
      tone: "hp",
    },
    {
      key: "stamina",
      label: "Ausdauer",
      current: readNumber(resources?.sta_current) ?? readNumber(party?.sta_current),
      max: readNumber(resources?.sta_max) ?? readNumber(party?.sta_max),
      tone: "stamina",
    },
    {
      key: "resource",
      label: resourceName,
      current: readNumber(resources?.res_current) ?? readNumber(party?.res_current),
      max: readNumber(resources?.res_max) ?? readNumber(party?.res_max),
      tone: "essence",
    },
  ];
}

function topSkills(sheet: CharacterSheetResponse | null): ActorDockView["skills"] {
  return (sheet?.sheet.skills ?? [])
    .slice()
    .sort((left, right) => {
      const leftMatch = left.class_match ? 1 : 0;
      const rightMatch = right.class_match ? 1 : 0;
      return rightMatch - leftMatch || (right.level ?? 0) - (left.level ?? 0) || String(right.rank ?? "").localeCompare(String(left.rank ?? ""));
    })
    .slice(0, 3)
    .map((skill) => ({
      id: skill.id || skill.name || "skill",
      name: skill.name || skill.id || "Unbenannte Fertigkeit",
      value: skill.rank ? `Rang ${skill.rank}` : `Stufe ${skill.level ?? 1}`,
      class_match: skill.class_match === true,
    }));
}

function equipmentPreview(sheet: CharacterSheetResponse | null): ActorDockView["equipment"] {
  const equipment = readRecord(sheet?.sheet.gear_inventory.equipment);
  const preferred = ["weapon", "mainhand", "chest", "armor", "cloak", "amulet", "trinket", "relic"];
  return Object.entries(equipment)
    .sort(([left], [right]) => preferred.indexOf(left) - preferred.indexOf(right))
    .map(([slot, value]) => ({
      slot: titleize(slot),
      name: readString(readRecord(value).name) || "Leer",
    }))
    .filter((entry) => entry.name !== "Leer")
    .slice(0, 3);
}

function importantItems(sheet: CharacterSheetResponse | null): ActorDockView["items"] {
  return (sheet?.sheet.gear_inventory.inventory_items ?? [])
    .filter((item) => item.rarity !== "common" || item.slot === "quest" || item.cursed)
    .slice(0, 4)
    .map((item) => ({ id: item.item_id, name: item.name }));
}

function bondPreview(campaign: CampaignSnapshot, slot_id: string): ActorDockView["bonds"] {
  const profile = livingProfile(campaign, slot_id);
  const social = readRecord(profile.social_model);
  const specific = readRecord(social.specific_bonds);
  const bonds = Object.entries(specific)
    .map(([id, value]) => {
      const record = readRecord(value);
      return { id, name: firstString(record.name, id), detail: firstString(record.trust, record.tension, record.status) || "Bindung" };
    })
    .slice(0, 3);
  if (bonds.length > 0) {
    return bonds;
  }
  return readArray(social.relationship_patterns)
    .map((value, index) => ({ id: `pattern-${index}`, name: readString(value), detail: "Muster" }))
    .filter((entry) => entry.name)
    .slice(0, 3);
}

export function deriveActorDockView(
  campaign: CampaignSnapshot,
  slot_id: string,
  sheet: CharacterSheetResponse | null,
): ActorDockView {
  const party = asFallbackPartyEntry(campaign, slot_id);
  const overview = sheet?.sheet.overview;
  const bio = readRecord(overview?.bio);
  const profile = livingProfile(campaign, slot_id);
  const body = readRecord(profile.body_state);
  const needs = readRecord(profile.needs_model);
  const classCurrent = overview?.class_current ?? sheet?.sheet.class.current ?? null;
  const progression = overview?.character_progression;
  const conditions = readArray(party?.conditions).map(readString).filter(Boolean);
  const effectsCount = sheet?.sheet.effects?.length ?? 0;
  const factions = readArray(sheet?.sheet.meta?.faction_memberships)
    .map((entry) => firstString(readRecord(entry).name, readRecord(entry).faction_id))
    .filter(Boolean)
    .slice(0, 2);

  return {
    slot_id,
    display_name: sheet?.display_name || party?.display_name || FALLBACK_NAME,
    species: firstString(bio.species, bio.race, bio.volk) || "Volk unbekannt",
    class_name: classCurrent?.name || party?.class_name || "Rolle unbekannt",
    class_rank: classCurrent?.rank || party?.class_rank || "Rang F",
    level: readNumber(progression?.level) ?? readNumber(classCurrent?.level) ?? readNumber(party?.level) ?? readNumber(party?.class_level),
    xp_current: readNumber(progression?.xp_current) ?? readNumber(classCurrent?.xp),
    xp_to_next: readNumber(progression?.xp_to_next) ?? readNumber(classCurrent?.xp_next),
    active: viewerClaimedSlotId(campaign) === slot_id,
    karma_label: deriveKarmaLabel(campaign, slot_id),
    scene_label: resolveSceneLabel(
      campaign,
      sheet?.scene_id ?? party?.scene_id,
      sheet?.scene_name ?? party?.scene_name,
    ),
    resources: resourceMeters(sheet, party),
    conditions,
    injury_count: readNumber(overview?.injury_count) ?? sheet?.sheet.injuries_scars.injuries.length ?? party?.injury_count ?? 0,
    scar_count: readNumber(overview?.scar_count) ?? sheet?.sheet.injuries_scars.scars.length ?? party?.scar_count ?? 0,
    effects_count: effectsCount,
    can_act_label: conditions.length === 0 ? "Handlungsfaehig" : "Eingeschraenkt",
    body_energy: firstString(body.energy) || "ruhig",
    body_pain: firstString(body.pain) || "keiner",
    pressure: firstString(needs.current_pressure) || "kein akuter Druck",
    skills: topSkills(sheet),
    equipment: equipmentPreview(sheet),
    items: importantItems(sheet),
    bonds: bondPreview(campaign, slot_id),
    factions,
  };
}

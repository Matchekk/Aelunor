import type { CampaignSnapshot, CharacterSheetResponse, NpcSheetResponse } from "../../shared/api/contracts";
import { getNoveltyCount, noveltyLabel } from "../play/novelty";
import type { CodexKind, DrawerType } from "./drawerStore";

export interface DrawerTabConfig {
  id: string;
  label: string;
  novelty_label: string | null;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function readArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function deriveDrawerTabs(
  drawer_type: DrawerType,
  campaign_id: string,
  entity_id: string,
  codex_kind: CodexKind | null,
): DrawerTabConfig[] {
  const tabs =
    drawer_type === "npc"
      ? [
          { id: "overview", label: "Overview" },
          { id: "class", label: "Goal" },
          { id: "attributes", label: "History" },
          { id: "skills", label: "Links" },
        ]
      : drawer_type === "codex"
        ? [
            { id: "overview", label: "Overview" },
            { id: "class", label: "Identity" },
            { id: "attributes", label: "Origin" },
            { id: "skills", label: "Traits" },
            { id: "injuries", label: "Abilities" },
            { id: "gear", label: "Lore" },
          ]
        : [
            { id: "overview", label: "Overview" },
            { id: "class", label: "Class" },
            { id: "attributes", label: "Attributes" },
            { id: "skills", label: "Skills" },
            { id: "injuries", label: "Injuries" },
            { id: "gear", label: "Gear" },
          ];

  return tabs.map((tab) => {
    let noveltyCount = 0;
    if (drawer_type === "character") {
      noveltyCount =
        tab.id === "skills"
          ? getNoveltyCount(campaign_id, `skill:${entity_id}`)
          : tab.id === "class"
            ? getNoveltyCount(campaign_id, `class:${entity_id}`)
            : tab.id === "injuries"
              ? getNoveltyCount(campaign_id, `injury:${entity_id}`)
              : 0;
    }
    if (drawer_type === "codex" && codex_kind) {
      noveltyCount =
        codex_kind === "beast"
          ? getNoveltyCount(campaign_id, `codex:beast:${entity_id}`) + getNoveltyCount(campaign_id, `beast:new:${entity_id}`)
          : getNoveltyCount(campaign_id, `codex:race:${entity_id}`);
    }
    return {
      ...tab,
      novelty_label: noveltyLabel(noveltyCount),
    };
  });
}

export function deriveCharacterDrawerSubtitle(sheet: CharacterSheetResponse): string {
  const scene = sheet.scene_name || sheet.scene_id || "Unknown scene";
  const claim = sheet.claimed_by_name ? ` • ${sheet.claimed_by_name}` : "";
  return `${scene}${claim}`;
}

export function deriveNpcDrawerSubtitle(sheet: NpcSheetResponse): string {
  const race = sheet.race || "Unknown";
  const level = typeof sheet.level === "number" ? ` • Lv ${sheet.level}` : "";
  return `${race}${level}`;
}

export function deriveNpcPreview(campaign: CampaignSnapshot): Array<{ npc_id: string; name: string; role_hint: string; scene_name: string }> {
  const state = readRecord(campaign.state);
  const summary = readArray(state.npc_codex_summary);
  return summary
    .map((entry) => readRecord(entry))
    .filter((entry) => readString(entry.npc_id) && readString(entry.name))
    .slice(0, 4)
    .map((entry) => ({
      npc_id: readString(entry.npc_id),
      name: readString(entry.name),
      role_hint: readString(entry.role_hint),
      scene_name: readString(entry.last_seen_scene_name),
    }));
}

export interface CodexDrawerPayload {
  kind: CodexKind;
  entity_id: string;
  name: string;
  knowledge_level: number;
  profile: Record<string, unknown>;
  entry: Record<string, unknown>;
}

export function deriveCodexPreview(
  campaign: CampaignSnapshot,
): Array<{ kind: CodexKind; entity_id: string; name: string; knowledge_level: number; novelty_label: string | null }> {
  const state = readRecord(campaign.state);
  const codex = readRecord(state.codex);
  const world = readRecord(state.world);
  const raceEntries = Object.entries(readRecord(codex.races))
    .map(([entity_id, entry]) => {
      const record = readRecord(entry);
      const level = Number(record.knowledge_level || 0);
      const profile = readRecord(readRecord(world.races)[entity_id]);
      if (level <= 0 || !readString(profile.name)) {
        return null;
      }
      return {
        kind: "race" as const,
        entity_id,
        name: readString(profile.name),
        knowledge_level: level,
        novelty_label: noveltyLabel(getNoveltyCount(campaign.campaign_meta.campaign_id, `codex:race:${entity_id}`)),
      };
    })
    .filter((entry): entry is NonNullable<typeof entry> => Boolean(entry));
  const beastEntries = Object.entries(readRecord(codex.beasts))
    .map(([entity_id, entry]) => {
      const record = readRecord(entry);
      const level = Number(record.knowledge_level || 0);
      const profile = readRecord(readRecord(world.beast_types)[entity_id]);
      if (level <= 0 || !readString(profile.name)) {
        return null;
      }
      return {
        kind: "beast" as const,
        entity_id,
        name: readString(profile.name),
        knowledge_level: level,
        novelty_label: noveltyLabel(
          getNoveltyCount(campaign.campaign_meta.campaign_id, `codex:beast:${entity_id}`) +
            getNoveltyCount(campaign.campaign_meta.campaign_id, `beast:new:${entity_id}`),
        ),
      };
    })
    .filter((entry): entry is NonNullable<typeof entry> => Boolean(entry));
  return [...raceEntries, ...beastEntries].slice(0, 6);
}

export function buildCodexDrawerPayload(
  campaign: CampaignSnapshot,
  kind: CodexKind,
  entity_id: string,
): CodexDrawerPayload | null {
  const state = readRecord(campaign.state);
  const world = readRecord(state.world);
  const codex = readRecord(state.codex);
  const profile = kind === "race" ? readRecord(readRecord(world.races)[entity_id]) : readRecord(readRecord(world.beast_types)[entity_id]);
  const entry = kind === "race" ? readRecord(readRecord(codex.races)[entity_id]) : readRecord(readRecord(codex.beasts)[entity_id]);
  const name = readString(profile.name);
  if (!name) {
    return null;
  }
  return {
    kind,
    entity_id,
    name,
    knowledge_level: Number(entry.knowledge_level || 0),
    profile,
    entry,
  };
}

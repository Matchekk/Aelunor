import type { CampaignSnapshot } from "../../shared/api/contracts";
import { deriveTimelineEntries, type TimelineEntry } from "../play/selectors";

export type SceneFilterId = "all" | string;

export interface SceneOption {
  scene_id: SceneFilterId;
  scene_name: string;
  member_count: number;
}

export interface SceneMember {
  slot_id: string;
  display_name: string;
  class_name: string | null;
  scene_id: string | null;
  scene_name: string | null;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export function deriveSceneNameMap(campaign: CampaignSnapshot): Record<string, string> {
  const sceneNames: Record<string, string> = {};
  const state = readRecord(campaign.state);
  const scenes = readRecord(state.scenes);
  for (const [scene_id, entry] of Object.entries(scenes)) {
    const sceneName = readString(readRecord(entry).name);
    if (sceneName) {
      sceneNames[scene_id] = sceneName;
    }
  }

  const nodes = readRecord(readRecord(state.map).nodes);
  for (const [scene_id, entry] of Object.entries(nodes)) {
    const nodeName = readString(readRecord(entry).name);
    if (nodeName && !sceneNames[scene_id]) {
      sceneNames[scene_id] = nodeName;
    }
  }

  for (const entry of campaign.party_overview) {
    if (entry.scene_id && entry.scene_name && !sceneNames[entry.scene_id]) {
      sceneNames[entry.scene_id] = entry.scene_name;
    }
  }

  for (const entry of deriveTimelineEntries(campaign)) {
    if (entry.scene_id && entry.scene_name && !sceneNames[entry.scene_id]) {
      sceneNames[entry.scene_id] = entry.scene_name;
    }
  }

  return sceneNames;
}

export function deriveSceneOptions(campaign: CampaignSnapshot): SceneOption[] {
  const sceneNames = deriveSceneNameMap(campaign);
  const counts = new Map<string, number>();

  for (const member of campaign.party_overview) {
    if (member.scene_id) {
      counts.set(member.scene_id, (counts.get(member.scene_id) ?? 0) + 1);
    }
  }

  for (const entry of deriveTimelineEntries(campaign)) {
    if (entry.scene_id && !counts.has(entry.scene_id)) {
      counts.set(entry.scene_id, 0);
    }
  }

  const rows = Array.from(counts.entries())
    .map(([scene_id, member_count]) => ({
      scene_id,
      scene_name: sceneNames[scene_id] || scene_id,
      member_count,
    }))
    .sort((left, right) => {
      if (right.member_count !== left.member_count) {
        return right.member_count - left.member_count;
      }
      return left.scene_name.localeCompare(right.scene_name);
    });

  return [
    {
      scene_id: "all",
      scene_name: "Alle Szenen",
      member_count: campaign.party_overview.length,
    },
    ...rows,
  ];
}

export function deriveSceneMembership(campaign: CampaignSnapshot, selected_scene_id: SceneFilterId): SceneMember[] {
  const members = campaign.party_overview.map((entry) => ({
    slot_id: entry.slot_id,
    display_name: entry.display_name,
    class_name: entry.class_name || null,
    scene_id: entry.scene_id || null,
    scene_name: entry.scene_name || null,
  }));

  if (selected_scene_id === "all") {
    return members;
  }

  return members.filter((entry) => entry.scene_id === selected_scene_id);
}

export function deriveFilteredTimelineEntries(campaign: CampaignSnapshot, selected_scene_id: SceneFilterId): TimelineEntry[] {
  const entries = deriveTimelineEntries(campaign);
  if (selected_scene_id === "all") {
    return entries;
  }
  return entries.filter((entry) => entry.scene_id === selected_scene_id);
}

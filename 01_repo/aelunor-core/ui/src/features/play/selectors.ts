import type {
  CampaignSnapshot,
  IntroStateSnapshot,
  PresenceActivity,
  PresenceBlockingAction,
  TurnRequest,
} from "../../shared/api/contracts";
import type { PlayModeId } from "./modeConfig";
import { getPlayModeConfig } from "./modeConfig";

export interface TimelineEntry {
  turn_id: string;
  turn_number: number | null;
  actor_id: string;
  actor_display: string;
  mode: string;
  input_text_display: string;
  gm_text_display: string;
  created_at: string;
  patch_summary_label: string | null;
  patch_summary: Record<string, number>;
  scene_id: string | null;
  scene_name: string | null;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function sceneNameFromState(campaign: CampaignSnapshot, scene_id: string): string | null {
  const state = readRecord(campaign.state);
  const scenes = readRecord(state.scenes);
  const scene = readRecord(scenes[scene_id]);
  const sceneName = readString(scene.name);
  if (sceneName) {
    return sceneName;
  }

  const map = readRecord(state.map);
  const nodes = readRecord(map.nodes);
  const node = readRecord(nodes[scene_id]);
  const nodeName = readString(node.name);
  return nodeName || null;
}

function readSceneFromPatch(patch_value: unknown, actor_id: string, campaign: CampaignSnapshot): { scene_id: string | null; scene_name: string | null } {
  const patch = readRecord(patch_value);
  const characters = readRecord(patch.characters);
  const actorPatch = readRecord(characters[actor_id]);
  const scene_id = readString(actorPatch.scene_id);
  if (!scene_id) {
    return { scene_id: null, scene_name: null };
  }
  return {
    scene_id,
    scene_name: sceneNameFromState(campaign, scene_id),
  };
}

function deriveTurnScene(turn: CampaignSnapshot["active_turns"][number], campaign: CampaignSnapshot): { scene_id: string | null; scene_name: string | null } {
  const direct_scene_id = readString(turn.scene_id);
  if (direct_scene_id) {
    return {
      scene_id: direct_scene_id,
      scene_name: readString(turn.scene_name) || sceneNameFromState(campaign, direct_scene_id),
    };
  }

  const narratorScene = readSceneFromPatch(turn.narrator_patch, turn.actor, campaign);
  if (narratorScene.scene_id) {
    return narratorScene;
  }

  const extractorScene = readSceneFromPatch(turn.extractor_patch, turn.actor, campaign);
  if (extractorScene.scene_id) {
    return extractorScene;
  }

  return { scene_id: null, scene_name: null };
}

function formatDateTime(value: string): string | null {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) {
    return null;
  }
  return new Date(timestamp).toLocaleString();
}

function sumPatchChanges(value: unknown): number {
  const patch = readRecord(value);
  return Object.values(patch).reduce<number>((total, entry) => {
    const numeric = typeof entry === "number" ? entry : 0;
    return total + (Number.isFinite(numeric) ? numeric : 0);
  }, 0);
}

function normalizePatchSummary(value: unknown): Record<string, number> {
  const patch = readRecord(value);
  const normalized: Record<string, number> = {};
  for (const [key, rawValue] of Object.entries(patch)) {
    if (typeof rawValue !== "number" || !Number.isFinite(rawValue) || rawValue <= 0) {
      continue;
    }
    normalized[key] = Math.round(rawValue);
  }
  return normalized;
}

export function deriveTimelineEntries(campaign: CampaignSnapshot): TimelineEntry[] {
  return (campaign.active_turns ?? [])
    .map((turn) => {
      const patch_summary = normalizePatchSummary(turn.patch_summary);
      const patchChangeCount = sumPatchChanges(patch_summary);
      const scene = deriveTurnScene(turn, campaign);
      return {
        turn_id: turn.turn_id,
        turn_number: turn.turn_number,
        actor_id: turn.actor || "",
        actor_display: turn.actor_display || turn.actor || "Unknown actor",
        mode: turn.mode || turn.action_type || "TURN",
        input_text_display: turn.input_text_display || "",
        gm_text_display: turn.gm_text_display || "",
        created_at: turn.created_at,
        patch_summary_label: patchChangeCount > 0 ? `${patchChangeCount} state changes` : null,
        patch_summary,
        scene_id: scene.scene_id,
        scene_name: scene.scene_name,
      };
    })
    .sort((left, right) => {
      const leftNumber = left.turn_number ?? 0;
      const rightNumber = right.turn_number ?? 0;
      return rightNumber - leftNumber;
    });
}

const PATCH_SUMMARY_LABELS: Record<string, string> = {
  characters_changed: "Characters changed",
  items_added: "Items added",
  plot_updates: "Plot updates",
  map_updates: "Map updates",
  events_added: "Events added",
};

export interface TurnDeltaRow {
  key: string;
  label: string;
  value: number;
}

export function deriveTurnDeltaRows(entry: TimelineEntry): TurnDeltaRow[] {
  return Object.entries(entry.patch_summary)
    .filter(([, value]) => value > 0)
    .sort((left, right) => right[1] - left[1])
    .map(([key, value]) => ({
      key,
      label: PATCH_SUMMARY_LABELS[key] ?? key.replace(/_/g, " "),
      value,
    }));
}

export function deriveViewerSummary(campaign: CampaignSnapshot): string {
  const parts: string[] = [];
  const display_name = campaign.viewer_context.display_name;
  if (display_name) {
    parts.push(display_name);
  }
  parts.push(campaign.viewer_context.is_host ? "Host" : "Player");
  if (campaign.viewer_context.claimed_slot_id) {
    parts.push(`Claim ${campaign.viewer_context.claimed_slot_id}`);
  } else {
    parts.push("No claim yet");
  }
  return parts.join(" • ");
}

export function derivePartySummary(campaign: CampaignSnapshot): string {
  const party_count = campaign.display_party.length;
  const total_slots = campaign.character_sheet_slots.length;
  return `${party_count} active of ${total_slots} slots`;
}

export function derivePresenceSummary(
  sse_connected: boolean,
  activities: Record<string, PresenceActivity>,
  blocking_action: PresenceBlockingAction | null,
): string {
  if (blocking_action?.label) {
    return blocking_action.label;
  }
  const activityCount = Object.keys(activities).length;
  if (!sse_connected) {
    return "Live presence is reconnecting.";
  }
  if (activityCount === 0) {
    return "No live activity yet.";
  }
  return `${activityCount} live presence event${activityCount === 1 ? "" : "s"}`;
}

export function formatTimelineTimestamp(value: string): string {
  return formatDateTime(value) ?? "Unknown time";
}

export function deriveTurnLead(entry: TimelineEntry): string {
  if (entry.input_text_display) {
    return entry.input_text_display;
  }
  return "No player-facing input text.";
}

export function deriveTurnOutcome(entry: TimelineEntry): string {
  if (entry.gm_text_display) {
    return entry.gm_text_display;
  }
  return "No GM response text yet.";
}

function deriveCampaignPhase(campaign: CampaignSnapshot): string {
  const meta = readRecord(campaign.state).meta;
  return readString(readRecord(meta).phase) || campaign.viewer_context.phase || campaign.campaign_meta.status || "unknown";
}

function latestTurn(campaign: CampaignSnapshot) {
  return campaign.active_turns.length > 0 ? campaign.active_turns[campaign.active_turns.length - 1] : null;
}

export function deriveIntroState(campaign: CampaignSnapshot): IntroStateSnapshot {
  const meta = readRecord(campaign.state).meta;
  const intro = readRecord(readRecord(meta).intro_state);
  return {
    status: readString(intro.status) || "idle",
    last_error: readString(intro.last_error),
    last_attempt_at: readString(intro.last_attempt_at),
    generated_turn_id: readString(intro.generated_turn_id),
  };
}

export function campaignHasIntro(campaign: CampaignSnapshot): boolean {
  return campaign.active_turns.length > 0;
}

export function deriveLatestRequests(campaign: CampaignSnapshot, actor: string | null): TurnRequest[] {
  const turn = latestTurn(campaign);
  if (!turn) {
    return [];
  }
  return (turn.requests ?? []).filter((request) => !request.actor || !actor || request.actor === actor);
}

export interface ComposerAccessState {
  actor: string | null;
  can_submit: boolean;
  submit_label: string;
  disabled_reason: string | null;
  helper_text: string;
  requires_input: boolean;
}

export function deriveComposerAccessState(
  campaign: CampaignSnapshot,
  mode: PlayModeId,
  blocking_action: PresenceBlockingAction | null,
  submit_pending: boolean,
  draft: string,
): ComposerAccessState {
  const actor = campaign.viewer_context.claimed_slot_id ?? null;
  const config = getPlayModeConfig(mode);
  const phase = deriveCampaignPhase(campaign);
  const intro = deriveIntroState(campaign);
  const hasIntro = campaignHasIntro(campaign);
  const normalizedDraft = draft.trim();

  let disabled_reason: string | null = null;
  let requires_input = false;

  if (!actor) {
    disabled_reason = "Without a claimed slot you can read, but you cannot submit.";
  } else if (submit_pending) {
    disabled_reason = config.is_contextual ? "Context query is running." : "Your turn is being submitted.";
  } else if (blocking_action?.label) {
    disabled_reason = "A shared campaign action is still processing. Wait for it to finish before sending anything new.";
  } else if (phase !== "active") {
    disabled_reason = "Turns only open once the campaign phase is active.";
  } else if (!hasIntro && intro.status === "failed") {
    disabled_reason = "The campaign intro failed and needs to be retried before turns can be sent.";
  } else if (!hasIntro) {
    disabled_reason = "The opening GM intro has not appeared yet.";
  } else if (!normalizedDraft) {
    requires_input = true;
  }

  const helper_text = disabled_reason
    ? disabled_reason
    : requires_input
      ? "Write a draft before submitting."
    : config.id === "canon"
      ? "This contribution will be treated as canon and should change the world deliberately."
      : config.id === "context"
        ? "This asks a canon/context question and does not create a new story turn."
        : `The GM will interpret this ${config.label.toLowerCase()} contribution inside the current scene.`;

  return {
    actor,
    can_submit: disabled_reason === null && !requires_input,
    submit_label: config.is_contextual ? "Ask context" : "Send turn",
    disabled_reason,
    helper_text,
    requires_input,
  };
}

export function deriveIntroBannerMessage(campaign: CampaignSnapshot): string | null {
  const intro = deriveIntroState(campaign);
  if (campaignHasIntro(campaign)) {
    return null;
  }
  if (intro.status === "failed") {
    return intro.last_error || "The campaign intro failed. Retry is still handled in the legacy UI.";
  }
  if (intro.status === "pending") {
    return "The GM intro is still being prepared.";
  }
  return "The campaign is waiting for its first GM intro turn.";
}

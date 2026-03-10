import type {
  AvailableSlotSnapshot,
  CampaignPlayer,
  CampaignSnapshot,
  PresenceActivity,
  SetupReadyCounter,
  SetupSlotStatus,
} from "../../shared/api/contracts";

export interface ClaimGateState {
  current_slot_id: string | null;
  needs_claim: boolean;
  needs_world_setup: boolean;
  needs_character_setup: boolean;
  can_enter_play: boolean;
  requires_claim_workspace: boolean;
  phase: string;
  phase_display: string;
  ready_counter: SetupReadyCounter;
  blocking_reason: string | null;
}

export interface ClaimSlotViewModel {
  slot_id: string;
  display_name: string;
  claimed_by: string | null;
  claimed_by_name: string | null;
  is_mine: boolean;
  is_free: boolean;
  is_ready: boolean;
  status_label: string;
  readiness_label: string;
  summary: string;
  can_claim: boolean;
  can_take_over: boolean;
  can_unclaim: boolean;
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function readBoolean(value: unknown): boolean {
  return value === true;
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function playersById(players: CampaignPlayer[]): Record<string, CampaignPlayer> {
  return players.reduce<Record<string, CampaignPlayer>>((acc, player) => {
    acc[player.player_id] = player;
    return acc;
  }, {});
}

function slotStatusesById(statuses: SetupSlotStatus[] | undefined): Record<string, SetupSlotStatus> {
  return (statuses ?? []).reduce<Record<string, SetupSlotStatus>>((acc, status) => {
    acc[status.slot_id] = status;
    return acc;
  }, {});
}

function deriveReadyCounter(campaign: CampaignSnapshot): SetupReadyCounter {
  const ready_counter = campaign.setup_runtime.ready_counter ?? campaign.setup_runtime.world?.ready_counter;
  if (ready_counter) {
    return {
      ready: readNumber(ready_counter.ready) ?? 0,
      total: readNumber(ready_counter.total) ?? 0,
    };
  }

  const statuses = campaign.setup_runtime.slot_statuses ?? campaign.setup_runtime.world?.slot_statuses ?? [];
  return {
    ready: statuses.filter((status) => status.status === "ready" || status.completed).length,
    total: statuses.length,
  };
}

function deriveBlockingReason(gate: ClaimGateState): string | null {
  if (gate.needs_world_setup) {
    return "World setup is not complete yet. Slot claiming stays blocked until the world is ready.";
  }
  if (gate.needs_claim) {
    return "Choose a slot to continue into the campaign.";
  }
  if (gate.needs_character_setup) {
    return "You have a claimed slot, but character setup still needs to be completed before play opens.";
  }
  if (!gate.can_enter_play) {
    return "This session is not ready to enter the campaign workspace yet.";
  }
  return null;
}

function deriveSlotSummary(slot: AvailableSlotSnapshot): string {
  const focus = readString(readRecord(slot.summary).current_focus);
  if (slot.completed) {
    const classBits = [slot.class_name || "No class"];
    if (slot.class_rank) {
      classBits.push(`(${slot.class_rank})`);
    }
    if (focus) {
      classBits.push(`• ${focus}`);
    }
    return classBits.join(" ");
  }
  return "No finished character build in this slot yet.";
}

function deriveSlotStatusLabel(
  slot: AvailableSlotSnapshot,
  is_mine: boolean,
): string {
  if (is_mine) {
    return slot.completed ? "Your claimed slot • ready" : "Your claimed slot";
  }
  if (!slot.claimed_by) {
    return "Free";
  }
  return `Occupied by ${slot.claimed_by_name || "another player"}`;
}

function deriveReadinessLabel(
  slot: AvailableSlotSnapshot,
  setup_status: SetupSlotStatus | undefined,
  gate: ClaimGateState,
): string {
  if (gate.needs_world_setup) {
    return "World setup must finish before any slot can be claimed.";
  }

  const normalized_status = setup_status?.status ?? (slot.completed ? "ready" : slot.claimed_by ? "in_progress" : "unclaimed");
  if (normalized_status === "ready") {
    return "Character setup complete.";
  }
  if (normalized_status === "in_progress") {
    return "Character setup in progress.";
  }
  return "Waiting for a player claim.";
}

export function deriveClaimGateState(campaign: CampaignSnapshot): ClaimGateState {
  const current_slot_id = campaign.viewer_context.claimed_slot_id ?? null;
  const needs_world_setup =
    campaign.viewer_context.needs_world_setup || !readBoolean(campaign.setup_runtime.world?.completed);
  const needs_claim = !current_slot_id;
  const needs_character_setup =
    Boolean(current_slot_id) &&
    (campaign.viewer_context.needs_character_setup || campaign.setup_runtime.character?.is_review_step === false);
  const phase = campaign.viewer_context.phase || campaign.setup_runtime.phase || campaign.campaign_meta.status || "unknown";
  const phase_display = campaign.setup_runtime.phase_display || phase;
  const ready_counter = deriveReadyCounter(campaign);

  const can_enter_play = Boolean(current_slot_id) && !needs_world_setup && !needs_character_setup;
  const gate: ClaimGateState = {
    current_slot_id,
    needs_claim,
    needs_world_setup,
    needs_character_setup,
    can_enter_play,
    requires_claim_workspace: !can_enter_play,
    phase,
    phase_display,
    ready_counter,
    blocking_reason: null,
  };

  return {
    ...gate,
    blocking_reason: deriveBlockingReason(gate),
  };
}

export function deriveClaimSlots(campaign: CampaignSnapshot): ClaimSlotViewModel[] {
  const gate = deriveClaimGateState(campaign);
  const current_slot_id = gate.current_slot_id;
  const player_index = playersById(campaign.players);
  const setup_status_index = slotStatusesById(campaign.setup_runtime.slot_statuses ?? campaign.setup_runtime.world?.slot_statuses);

  return (campaign.available_slots ?? []).map((slot) => {
    const claimed_by = slot.claimed_by ?? null;
    const claimed_by_name = slot.claimed_by_name ?? player_index[claimed_by ?? ""]?.display_name ?? null;
    const is_mine = Boolean(current_slot_id && current_slot_id === slot.slot_id);
    const is_free = !claimed_by;
    const is_ready = Boolean(slot.completed);
    const setup_status = setup_status_index[slot.slot_id];
    const can_claim = !gate.needs_world_setup && !current_slot_id && is_free;
    const can_take_over = !gate.needs_world_setup && !is_mine && Boolean(claimed_by || current_slot_id);
    const can_unclaim = is_mine;

    return {
      slot_id: slot.slot_id,
      display_name: slot.display_name || slot.slot_id.toUpperCase(),
      claimed_by,
      claimed_by_name,
      is_mine,
      is_free,
      is_ready,
      status_label: deriveSlotStatusLabel({ ...slot, claimed_by_name }, is_mine),
      readiness_label: deriveReadinessLabel(slot, setup_status, gate),
      summary: deriveSlotSummary(slot),
      can_claim,
      can_take_over,
      can_unclaim,
    };
  });
}

export function deriveReadyProgressSummary(campaign: CampaignSnapshot): string {
  const ready_counter = deriveClaimGateState(campaign).ready_counter;
  if (ready_counter.total <= 0) {
    return "Readiness progress is not available yet.";
  }
  return `Ready ${ready_counter.ready}/${ready_counter.total}`;
}

export function deriveClaimMetaLine(campaign: CampaignSnapshot): string {
  const ready_counter = deriveClaimGateState(campaign).ready_counter;
  const parts = [
    `Session ${campaign.campaign_meta.campaign_id}`,
    `${campaign.players.length} players`,
    `Phase ${campaign.setup_runtime.phase_display || campaign.viewer_context.phase || campaign.campaign_meta.status}`,
  ];
  if (ready_counter.total > 0) {
    parts.push(`Ready ${ready_counter.ready}/${ready_counter.total}`);
  }
  return parts.join(" • ");
}

export function deriveClaimWorkspaceTarget(campaign: CampaignSnapshot): "claim" | "play" {
  return deriveClaimGateState(campaign).requires_claim_workspace ? "claim" : "play";
}

export function deriveClaimStatusMessage(campaign: CampaignSnapshot): string {
  const gate = deriveClaimGateState(campaign);
  if (gate.blocking_reason) {
    return gate.blocking_reason;
  }
  return "Claim a slot or continue into the campaign workspace.";
}

export function deriveSlotPresenceLabel(
  slot_id: string,
  owner_player_id: string | null,
  activities: Record<string, PresenceActivity>,
): string | null {
  const matchingBySlot = Object.values(activities).find((activity) => activity.slot_id === slot_id);
  if (matchingBySlot?.label) {
    return matchingBySlot.label;
  }
  if (owner_player_id && activities[owner_player_id]?.label) {
    return activities[owner_player_id].label;
  }
  return null;
}

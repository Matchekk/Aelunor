import type {
  CampaignSnapshot,
  SetupProgressPayload,
  SetupPromptState,
  SetupQuestionPayload,
  SetupReadyCounter,
} from "../../shared/api/contracts";

export type SetupFlowMode = "world" | "character";

export interface SetupGateState {
  requires_overlay: boolean;
  mode: SetupFlowMode | null;
  slot_id: string | null;
  needs_world_setup: boolean;
  needs_character_setup: boolean;
  can_enter_play: boolean;
  is_waiting: boolean;
  can_interact: boolean;
  phase_display: string;
  title: string;
  subtitle: string;
  current_prompt: SetupPromptState | null;
  current_question: SetupQuestionPayload | null;
  progress: SetupProgressPayload | null;
  chapter_progress: SetupProgressPayload | null;
  global_progress: SetupProgressPayload | null;
  chapter_label: string;
  chapter_index: number;
  chapter_total: number;
  ready_counter: SetupReadyCounter;
  has_review_step: boolean;
  is_random_available: boolean;
  summary_preview: Record<string, unknown>;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function readExistingAnswer(value: unknown): string | boolean | Record<string, unknown> | null {
  if (typeof value === "string" || typeof value === "boolean") {
    return value;
  }
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function readNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function coercePromptState(value: unknown): SetupPromptState | null {
  const record = readRecord(value);
  const question = readRecord(record.question);
  if (!readString(question.question_id) || !readString(question.type)) {
    return null;
  }

  return {
    question: {
      question_id: readString(question.question_id),
      label: readString(question.label) || "Untitled question",
      type: (readString(question.type) || "text") as SetupQuestionPayload["type"],
      required: question.required === true,
      options: Array.isArray(question.options)
        ? question.options.filter((entry): entry is string => typeof entry === "string")
        : [],
      option_entries: Array.isArray(question.option_entries)
        ? question.option_entries
            .map((entry) => readRecord(entry))
            .filter((entry) => readString(entry.value))
            .map((entry) => ({
              value: readString(entry.value),
              label: readString(entry.label) || readString(entry.value),
              ...(readString(entry.description) ? { description: readString(entry.description) } : {}),
            }))
        : [],
      min_selected: typeof question.min_selected === "number" ? question.min_selected : null,
      max_selected: typeof question.max_selected === "number" ? question.max_selected : null,
      allow_other: question.allow_other === true,
      ...(readString(question.other_hint) ? { other_hint: readString(question.other_hint) } : {}),
      ai_copy: readString(question.ai_copy),
      existing_answer: readExistingAnswer(question.existing_answer),
    },
    progress: {
      answered: readNumber(readRecord(record.progress).answered),
      total: readNumber(readRecord(record.progress).total),
      step: readNumber(readRecord(record.progress).step),
    },
  };
}

function deriveReadyCounter(campaign: CampaignSnapshot): SetupReadyCounter {
  const counter = campaign.setup_runtime.ready_counter ?? campaign.setup_runtime.world?.ready_counter;
  if (counter) {
    return {
      ready: readNumber(counter.ready),
      total: readNumber(counter.total),
    };
  }

  const statuses = campaign.setup_runtime.slot_statuses ?? campaign.setup_runtime.world?.slot_statuses ?? [];
  return {
    ready: statuses.filter((entry) => entry.completed || entry.status === "ready").length,
    total: statuses.length,
  };
}

function deriveSlotLabel(campaign: CampaignSnapshot, slot_id: string | null): string {
  if (!slot_id) {
    return "Character Setup";
  }

  const matchingAvailable = campaign.available_slots.find((slot) => slot.slot_id === slot_id);
  if (matchingAvailable?.display_name) {
    return matchingAvailable.display_name;
  }

  const matchingParty = campaign.party_overview.find((slot) => slot.slot_id === slot_id);
  if (matchingParty?.display_name) {
    return matchingParty.display_name;
  }

  return slot_id.toUpperCase();
}

export function deriveSetupGateState(campaign: CampaignSnapshot): SetupGateState {
  const slot_id = campaign.viewer_context.claimed_slot_id ?? null;
  const needs_world_setup = campaign.viewer_context.needs_world_setup || campaign.setup_runtime.world?.completed === false;
  const pending_prompt = coercePromptState(campaign.viewer_context.pending_setup_question);
  const world_prompt = campaign.setup_runtime.world?.next_question ?? (needs_world_setup ? pending_prompt : null);
  const character_prompt =
    campaign.setup_runtime.character?.question && campaign.setup_runtime.character?.progress
      ? {
          question: campaign.setup_runtime.character.question,
          progress: campaign.setup_runtime.character.progress,
        }
      : slot_id && campaign.viewer_context.needs_character_setup
        ? pending_prompt
        : null;
  const needs_character_setup = Boolean(slot_id) && (campaign.viewer_context.needs_character_setup || Boolean(character_prompt));

  const mode: SetupFlowMode | null = needs_world_setup ? "world" : needs_character_setup ? "character" : null;
  const runtime = mode === "world" ? campaign.setup_runtime.world : mode === "character" ? campaign.setup_runtime.character : null;
  const current_prompt = mode === "world" ? world_prompt : mode === "character" ? character_prompt : null;
  const progress = current_prompt?.progress ?? runtime?.progress ?? runtime?.global_progress ?? null;
  const chapter_progress = runtime?.chapter_progress ?? null;
  const global_progress = runtime?.global_progress ?? progress ?? null;
  const ready_counter = deriveReadyCounter(campaign);
  const is_waiting = mode === "world" && !campaign.viewer_context.is_host;
  const can_interact = mode === "world" ? campaign.viewer_context.is_host : mode === "character";
  const phase_display =
    campaign.setup_runtime.phase_display || campaign.viewer_context.phase || campaign.campaign_meta.status || "Setup";

  return {
    requires_overlay: mode !== null,
    mode,
    slot_id,
    needs_world_setup,
    needs_character_setup,
    can_enter_play: Boolean(slot_id) && !needs_world_setup && !needs_character_setup,
    is_waiting,
    can_interact,
    phase_display,
    title: mode === "world" ? "World Setup" : `Character Setup: ${deriveSlotLabel(campaign, slot_id)}`,
    subtitle:
      mode === "world"
        ? is_waiting
          ? "The host is defining the campaign frame. You can watch readiness progress here while the world is prepared."
          : "Define the campaign frame before slot claims and story play can begin."
        : "Finish the claimed character before the campaign can advance into playable story turns.",
    current_prompt,
    current_question: current_prompt?.question ?? null,
    progress,
    chapter_progress,
    global_progress,
    chapter_label: runtime?.chapter_label || (mode === "world" ? "World" : "Character"),
    chapter_index: readNumber(runtime?.chapter_index) || 1,
    chapter_total: readNumber(runtime?.chapter_total) || 1,
    ready_counter,
    has_review_step: runtime?.is_review_step === true || Boolean(runtime?.summary_preview),
    is_random_available: can_interact && Boolean(current_prompt?.question),
    summary_preview: readRecord(runtime?.summary_preview),
  };
}

export function canSkipQuestion(question: SetupQuestionPayload | null): boolean {
  return Boolean(question && !question.required);
}

export function deriveSetupProgressSummary(progress: SetupProgressPayload | null): string {
  if (!progress || progress.total <= 0) {
    return "Progress data is not available yet.";
  }
  return `Question ${progress.step}/${progress.total}`;
}

export function deriveSetupReviewEntries(summary_preview: Record<string, unknown>): Array<{ label: string; value: string }> {
  return Object.entries(summary_preview)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim().length > 0)
    .slice(0, 8)
    .map(([key, value]) => ({
      label: key.split("_").join(" "),
      value: Array.isArray(value) ? value.join(", ") : String(value),
    }));
}

export function deriveSetupWaitingMessage(campaign: CampaignSnapshot): string {
  const ready_counter = deriveSetupGateState(campaign).ready_counter;
  if (ready_counter.total > 0) {
    return `World setup is still in progress. Ready ${ready_counter.ready}/${ready_counter.total} claimed characters are finished so far.`;
  }
  return "World setup is still in progress. Wait for the host to finish defining the campaign frame.";
}

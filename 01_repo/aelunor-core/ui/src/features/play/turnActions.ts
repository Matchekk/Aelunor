import type { SubmitTurnRequest } from "../../shared/api/contracts";

export const CONTINUE_STORY_MARKER = "__CONTINUE_STORY__";

interface ContinueActionVisibilityInput {
  is_active_play: boolean;
  is_latest_turn: boolean;
  claimed_slot_id: string | null;
}

export function shouldShowContinueAction(input: ContinueActionVisibilityInput): boolean {
  return input.is_active_play && input.is_latest_turn && Boolean(input.claimed_slot_id);
}

export function buildContinueTurnPayload(actor: string): SubmitTurnRequest {
  return {
    actor,
    mode: "TUN",
    text: CONTINUE_STORY_MARKER,
  };
}

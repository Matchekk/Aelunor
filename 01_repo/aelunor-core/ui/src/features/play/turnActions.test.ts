import { describe, expect, it } from "vitest";

import { buildContinueTurnPayload, CONTINUE_STORY_MARKER, shouldShowContinueAction } from "./turnActions";

describe("turn action helpers", () => {
  it("builds continue marker payload with stable mode", () => {
    expect(buildContinueTurnPayload("slot_1")).toEqual({
      actor: "slot_1",
      mode: "TUN",
      text: CONTINUE_STORY_MARKER,
    });
  });

  it("shows continue action only for latest active turn with claim", () => {
    expect(
      shouldShowContinueAction({
        is_active_play: true,
        is_latest_turn: true,
        claimed_slot_id: "slot_1",
      }),
    ).toBe(true);
    expect(
      shouldShowContinueAction({
        is_active_play: false,
        is_latest_turn: true,
        claimed_slot_id: "slot_1",
      }),
    ).toBe(false);
    expect(
      shouldShowContinueAction({
        is_active_play: true,
        is_latest_turn: false,
        claimed_slot_id: "slot_1",
      }),
    ).toBe(false);
    expect(
      shouldShowContinueAction({
        is_active_play: true,
        is_latest_turn: true,
        claimed_slot_id: null,
      }),
    ).toBe(false);
  });
});

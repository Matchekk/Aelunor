import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import { deriveSetupGateState } from "./selectors";

describe("deriveSetupGateState", () => {
  it("puts non-host viewers into waiting world setup when world setup is incomplete", () => {
    const campaign = createCampaignFixture({
      viewer_context: {
        player_id: "player-2",
        display_name: "Guest",
        is_host: false,
        claimed_slot_id: null,
        claimed_character: null,
        phase: "world_setup",
        needs_world_setup: true,
        needs_character_setup: false,
        pending_setup_question: null,
      },
      setup_runtime: {
        phase: "world_setup",
        phase_display: "World Setup",
        world: {
          completed: false,
          ready_counter: {
            ready: 0,
            total: 2,
          },
        },
      },
    });

    const gate = deriveSetupGateState(campaign);
    expect(gate.requires_overlay).toBe(true);
    expect(gate.mode).toBe("world");
    expect(gate.is_waiting).toBe(true);
    expect(gate.can_interact).toBe(false);
  });

  it("uses character setup when the claimed slot still has pending questions", () => {
    const campaign = createCampaignFixture({
      viewer_context: {
        player_id: "player-host",
        display_name: "Host",
        is_host: true,
        claimed_slot_id: "aria",
        claimed_character: "Aria",
        phase: "character_setup_open",
        needs_world_setup: false,
        needs_character_setup: true,
        pending_setup_question: null,
      },
      setup_runtime: {
        phase: "character_setup_open",
        phase_display: "Character Setup",
        world: {
          completed: true,
        },
        claimed_slot_id: "aria",
        character: {
          question: {
            question_id: "q_origin",
            label: "Origin",
            type: "textarea",
            required: true,
            options: [],
            option_entries: [],
            allow_other: false,
            ai_copy: "Describe the origin.",
            existing_answer: null,
          },
          progress: {
            answered: 1,
            total: 3,
            step: 2,
          },
        },
      },
    });

    const gate = deriveSetupGateState(campaign);
    expect(gate.requires_overlay).toBe(true);
    expect(gate.mode).toBe("character");
    expect(gate.current_question?.question_id).toBe("q_origin");
    expect(gate.can_enter_play).toBe(false);
  });
});

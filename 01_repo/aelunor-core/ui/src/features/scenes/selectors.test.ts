import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import { deriveFilteredTimelineEntries, deriveSceneOptions } from "./selectors";

describe("scene selectors", () => {
  it("returns meaningful scene options when scene data exists", () => {
    const campaign = createCampaignFixture();

    const options = deriveSceneOptions(campaign);
    expect(options.length).toBeGreaterThan(1);
    expect(options.map((entry) => entry.scene_id)).toEqual(["all", "scene_forest", "scene_square"]);
  });

  it("filters timeline entries by scene without guessing unscoped turns", () => {
    const campaign = createCampaignFixture({
      active_turns: [
        {
          turn_id: "turn-1",
          turn_number: 1,
          status: "active",
          actor: "aria",
          actor_display: "Aria",
          action_type: "do",
          mode: "TUN",
          input_text_display: "Aria watches the square.",
          gm_text_display: "The market wakes slowly.",
          requests: [],
          created_at: "2026-03-10T10:01:00.000Z",
          updated_at: "2026-03-10T10:01:00.000Z",
          edit_count: 0,
          patch_summary: {},
          narrator_patch: {
            characters: {
              aria: {
                scene_id: "scene_square",
              },
            },
          },
          extractor_patch: {},
          can_edit: true,
          can_undo: true,
          can_retry: true,
        },
        {
          turn_id: "turn-2",
          turn_number: 2,
          status: "active",
          actor: "brann",
          actor_display: "Brann",
          action_type: "say",
          mode: "SAGEN",
          input_text_display: "Brann whispers into the trees.",
          gm_text_display: "Leaves answer with rain.",
          requests: [],
          created_at: "2026-03-10T10:02:00.000Z",
          updated_at: "2026-03-10T10:02:00.000Z",
          edit_count: 0,
          patch_summary: {},
          narrator_patch: {},
          extractor_patch: {},
          can_edit: true,
          can_undo: true,
          can_retry: true,
        },
      ],
    });

    expect(deriveFilteredTimelineEntries(campaign, "all")).toHaveLength(2);
    expect(deriveFilteredTimelineEntries(campaign, "scene_square").map((entry) => entry.turn_id)).toEqual(["turn-1"]);
  });
});

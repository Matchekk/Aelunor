import { describe, expect, it } from "vitest";

import {
  deriveInitialVisibleCount,
  deriveNextVisibleCount,
  deriveRenderedTimelineEntries,
  deriveTimelineWindow,
  INITIAL_TIMELINE_WINDOW,
} from "./timelineWindow";
import { createCampaignFixture } from "../../test/campaignFixture";
import { deriveTimelineEntries } from "./selectors";

describe("timelineWindow helpers", () => {
  it("starts with a bounded initial window", () => {
    expect(deriveInitialVisibleCount(0)).toBe(0);
    expect(deriveInitialVisibleCount(12)).toBe(12);
    expect(deriveInitialVisibleCount(INITIAL_TIMELINE_WINDOW + 20)).toBe(INITIAL_TIMELINE_WINDOW);
  });

  it("keeps older visible rows available when new turns arrive", () => {
    expect(
      deriveNextVisibleCount({
        previous_total_count: 48,
        next_total_count: 50,
        current_visible_count: 48,
        scene_changed: false,
      }),
    ).toBe(50);
  });

  it("resets to the initial window when the scene filter changes", () => {
    expect(
      deriveNextVisibleCount({
        previous_total_count: 120,
        next_total_count: 15,
        current_visible_count: 80,
        scene_changed: true,
      }),
    ).toBe(15);
  });

  it("derives visible and hidden counts safely", () => {
    expect(deriveTimelineWindow(100, 48)).toEqual({
      visible_count: 48,
      hidden_count: 52,
      can_load_more: true,
    });
  });

  it("slices rendered entries without mutating timeline order", () => {
    const campaign = createCampaignFixture({
      active_turns: Array.from({ length: 5 }, (_, index) => ({
        turn_id: `turn-${index + 1}`,
        turn_number: index + 1,
        status: "active",
        actor: "aria",
        actor_display: "Aria",
        action_type: "do",
        mode: "TUN",
        input_text_display: `Input ${index + 1}`,
        gm_text_display: `Outcome ${index + 1}`,
        requests: [],
        created_at: `2026-03-10T10:0${index}:00.000Z`,
        updated_at: `2026-03-10T10:0${index}:00.000Z`,
        edit_count: 0,
        patch_summary: {},
        narrator_patch: {},
        extractor_patch: {},
        can_edit: true,
        can_undo: true,
        can_retry: true,
      })),
    });

    const entries = deriveTimelineEntries(campaign);
    expect(deriveRenderedTimelineEntries(entries, 2).map((entry) => entry.turn_id)).toEqual(["turn-5", "turn-4"]);
  });
});

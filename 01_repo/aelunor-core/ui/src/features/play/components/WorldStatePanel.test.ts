import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../../test/campaignFixture";
import { deriveWorldStateSummary } from "./WorldStatePanel";

describe("deriveWorldStateSummary", () => {
  it("prefers structured campaign state and board objectives", () => {
    const base = createCampaignFixture();
    const campaign = createCampaignFixture({
      state: {
        meta: {
          phase: "active",
          turn: 7,
        },
        canon: {
          mode: "Strict",
        },
      },
      world_time: {
        weather: "Moonfall",
        time_of_day: "night",
      },
      boards: {
        ...base.boards,
        plot_essentials: {
          ...base.boards.plot_essentials,
          current_goal: "Find the moss gate",
          current_threat: "The roots remember",
        },
      },
    });

    expect(deriveWorldStateSummary(campaign)).toMatchObject({
      goal: "Find the moss gate",
      threat: "The roots remember",
      turn: 7,
      phase: "active",
      canon_mode: "Strict",
      weather: "Moonfall",
    });
  });

  it("falls back to safe labels when optional state is missing", () => {
    const base = createCampaignFixture();
    const campaign = createCampaignFixture({
      state: {
        meta: {},
      },
      boards: {
        ...base.boards,
        plot_essentials: {
          ...base.boards.plot_essentials,
          current_goal: "",
          current_threat: "",
        },
      },
      active_turns: [{ turn_id: "a" } as never, { turn_id: "b" } as never],
      world_time: {
        time_of_day: "dawn",
      },
    });

    expect(deriveWorldStateSummary(campaign)).toMatchObject({
      goal: "Noch kein Ziel festgelegt",
      threat: "Noch keine Bedrohung markiert",
      turn: 2,
      phase: "active",
      canon_mode: "Balanced",
      weather: "dawn",
    });
  });
});

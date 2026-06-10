import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import type { TimelineEntry } from "./selectors";
import { deriveShowModePill, deriveTimelineEntries, deriveTurnKindLabel, deriveTurnLead, deriveTurnOutcome } from "./selectors";

function entryWith(overrides: Partial<TimelineEntry>): TimelineEntry {
  return {
    turn_id: "turn-x",
    turn_number: 1,
    actor_id: "gm",
    actor_display: "GM",
    mode: "STORY",
    input_text_display: "",
    gm_text_display: "Der Schrein liegt still.",
    created_at: "2026-06-10T10:00:00.000Z",
    patch_summary_label: null,
    patch_summary: {},
    scene_id: null,
    scene_name: null,
    can_edit: false,
    can_undo: false,
    can_retry: false,
    ...overrides,
  };
}

describe("deriveTurnKindLabel", () => {
  it("labels player slots, system turns, and gm story turns", () => {
    const slots = ["aria", "brann"];
    expect(deriveTurnKindLabel(entryWith({ actor_id: "aria" }), slots)).toBe("Spieler");
    expect(deriveTurnKindLabel(entryWith({ actor_id: "gm", mode: "system" }), slots)).toBe("System");
    expect(deriveTurnKindLabel(entryWith({ actor_id: "gm" }), slots)).toBe("Story");
    expect(deriveTurnKindLabel(entryWith({ actor_id: "" }), [])).toBe("Story");
  });
});

describe("deriveShowModePill", () => {
  it("hides the mode pill when it would duplicate the kind badge", () => {
    expect(deriveShowModePill(entryWith({ actor_id: "gm", mode: "STORY" }), [])).toBe(false);
    expect(deriveShowModePill(entryWith({ actor_id: "gm", mode: "story" }), [])).toBe(false);
    expect(deriveShowModePill(entryWith({ actor_id: "aria", mode: "TUN" }), ["aria"])).toBe(true);
    expect(deriveShowModePill(entryWith({ actor_id: "gm", mode: "" }), [])).toBe(false);
  });
});

describe("journal entry rendering data", () => {
  it("renders one card model per turn and keeps fallbacks readable", () => {
    const campaign = createCampaignFixture();
    const entries = deriveTimelineEntries(campaign);
    expect(entries.length).toBe(1);
    expect(deriveTurnOutcome(entries[0]!)).toBe("The market wakes slowly.");
  });

  it("provides controlled fallback texts for empty content", () => {
    const empty = entryWith({ input_text_display: "", gm_text_display: "" });
    expect(deriveTurnLead(empty)).toBe("Kein sichtbarer Spielerbeitrag.");
    expect(deriveTurnOutcome(empty)).toBe("Noch kein sichtbarer Chroniktext.");
  });

  it("never produces undefined or [object Object] in card fields", () => {
    const campaign = createCampaignFixture({ active_turns: [{ turn_id: "broken" } as never] });
    for (const entry of deriveTimelineEntries(campaign)) {
      const rendered = [
        `Zug ${entry.turn_number ?? "?"}`,
        deriveTurnKindLabel(entry, []),
        entry.mode,
        entry.actor_display,
        deriveTurnLead(entry),
        deriveTurnOutcome(entry),
      ].join(" | ");
      expect(rendered).not.toContain("undefined");
      expect(rendered).not.toContain("[object Object]");
    }
  });

  it("returns an empty list for campaigns without turns (empty state path)", () => {
    const campaign = createCampaignFixture({ active_turns: [] });
    expect(deriveTimelineEntries(campaign)).toEqual([]);
  });
});

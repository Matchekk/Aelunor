import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import { deriveActorDockView } from "./actorDockModel";
import {
  FALLBACK_CLASS,
  FALLBACK_KARMA,
  FALLBACK_NAME,
  FALLBACK_RESOURCE_TEXT,
  FALLBACK_SCENE,
  derivePartyHud,
  formatResourceValue,
  resolveSceneLabel,
} from "./partyHudModel";

function collectStrings(value: unknown, out: string[] = []): string[] {
  if (typeof value === "string") {
    out.push(value);
  } else if (Array.isArray(value)) {
    value.forEach((entry) => collectStrings(entry, out));
  } else if (value && typeof value === "object") {
    Object.values(value).forEach((entry) => collectStrings(entry, out));
  }
  return out;
}

describe("formatResourceValue", () => {
  it("renders current/max and clamps out-of-range values", () => {
    expect(formatResourceValue(12, 20)).toMatchObject({ text: "12/20", percent: 60 });
    expect(formatResourceValue(-4, 20)).toMatchObject({ text: "0/20", percent: 0 });
    expect(formatResourceValue(35, 20)).toMatchObject({ text: "20/20", percent: 100 });
  });

  it("falls back to a dash when no real max exists", () => {
    expect(formatResourceValue(0, 0).text).toBe(FALLBACK_RESOURCE_TEXT);
    expect(formatResourceValue(undefined, undefined).text).toBe(FALLBACK_RESOURCE_TEXT);
    expect(formatResourceValue(5, -1).text).toBe(FALLBACK_RESOURCE_TEXT);
  });
});

describe("resolveSceneLabel", () => {
  it("prefers the explicit scene name, then state scenes, then map nodes", () => {
    const campaign = createCampaignFixture({
      state: {
        map: { nodes: { node_cliff: { name: "Cliff Path" } } },
      },
    });
    expect(resolveSceneLabel(campaign, "scene_square", "Marktplatz")).toBe("Marktplatz");
    expect(resolveSceneLabel(campaign, "scene_square", "")).toBe("Market Square");
    expect(resolveSceneLabel(campaign, "node_cliff", "")).toBe("Cliff Path");
    expect(resolveSceneLabel(campaign, "", "")).toBe(FALLBACK_SCENE);
  });
});

describe("derivePartyHud", () => {
  it("maps a normal campaign to readable character summaries", () => {
    const campaign = createCampaignFixture({
      party_overview: [
        {
          slot_id: "aria",
          display_name: "Aria",
          scene_id: "scene_square",
          scene_name: "Market Square",
          class_name: "Guard",
          class_rank: "D",
          class_level: 2,
          hp_current: 14,
          hp_max: 20,
          sta_current: 8,
          sta_max: 10,
          res_current: 3,
          res_max: 6,
          resource_name: "Aether",
          conditions: ["Erschöpft"],
          in_combat: true,
          injury_count: 1,
        },
      ],
      state: {
        characters: {
          aria: {
            journal: { reputation: ["Respektiert im Viertel", { faction: "Wache", standing: "vertraut" }] },
          },
        },
      },
    });

    const hud = derivePartyHud(campaign);
    expect(hud.party_count).toBe(1);
    expect(hud.characters[0]).toMatchObject({
      name: "Aria",
      class_label: "Guard · Rang D",
      level_label: "Lv 2",
      resource_name: "Aether",
      karma_label: "Respektiert im Viertel · Wache: vertraut",
      scene_label: "Market Square",
      in_combat: true,
      injury_count: 1,
      is_viewer: true,
    });
    expect(hud.characters[0]?.hp.text).toBe("14/20");
    expect(hud.characters[0]?.stamina.text).toBe("8/10");
    expect(hud.characters[0]?.resource.text).toBe("3/6");
  });

  it("uses controlled fallbacks when fields are missing", () => {
    const base = createCampaignFixture();
    const campaign = createCampaignFixture({
      party_overview: [{ slot_id: "slot_9", display_name: "" }],
      viewer_context: { ...base.viewer_context, claimed_slot_id: null, claimed_character: null },
    });

    const hud = derivePartyHud(campaign);
    expect(hud.characters[0]).toMatchObject({
      name: FALLBACK_NAME,
      class_label: FALLBACK_CLASS,
      level_label: "",
      karma_label: FALLBACK_KARMA,
      scene_label: FALLBACK_SCENE,
      is_viewer: false,
    });
    expect(hud.characters[0]?.hp.text).toBe(FALLBACK_RESOURCE_TEXT);
  });

  it("never renders undefined or [object Object] anywhere", () => {
    const campaign = createCampaignFixture({
      party_overview: [
        {
          slot_id: "slot_9",
          display_name: "",
          conditions: ["", "Blutung"],
        },
      ],
      state: {
        characters: {
          slot_9: {
            journal: { reputation: [{ weird: { nested: true } }, 42] },
          },
        },
      },
    });

    const rendered = collectStrings(derivePartyHud(campaign));
    for (const text of rendered) {
      expect(text).not.toContain("undefined");
      expect(text).not.toContain("[object Object]");
    }
  });
});

describe("deriveActorDockView state hud fields", () => {
  it("derives karma and scene labels with fallbacks and keeps bonds free of [object Object]", () => {
    const campaign = createCampaignFixture({
      state: {
        characters: {
          aria: {
            living_profile: {
              social_model: {
                relationship_patterns: [{ not: "a string" }, "beschützt Schwächere"],
              },
            },
          },
        },
      },
    });

    const view = deriveActorDockView(campaign, "aria", null);
    expect(view.karma_label).toBe(FALLBACK_KARMA);
    expect(view.scene_label).toBe("Market Square");
    expect(view.bonds.map((bond) => bond.name)).toEqual(["beschützt Schwächere"]);
  });

  it("falls back to an unnamed figure for unknown slots", () => {
    const campaign = createCampaignFixture();
    const view = deriveActorDockView(campaign, "slot_missing", null);
    expect(view.display_name).toBe(FALLBACK_NAME);
    expect(view.scene_label).toBe(FALLBACK_SCENE);
  });
});

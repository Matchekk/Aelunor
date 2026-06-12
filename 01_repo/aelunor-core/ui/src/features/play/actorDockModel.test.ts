import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import type { CharacterSheetResponse } from "../../shared/api/contracts";
import { deriveActorDockView } from "./actorDockModel";

function sheetWithGear(): CharacterSheetResponse {
  return {
    slot_id: "aria",
    display_name: "Aria",
    scene_id: "scene_square",
    scene_name: "Market Square",
    sheet: {
      overview: { bio: { species: "Mensch" } },
      class: { current: { name: "Guard", rank: "D", level: 2 } },
      effects: [],
      injuries_scars: { injuries: [], scars: [] },
      meta: { faction_memberships: [] },
      gear_inventory: {
        equipment: {
          weapon: { item_id: "item_sword", name: "Geschwungenes Langschwert", rarity: "rare", weight: 3 },
          chest: { item_id: null, name: "Leer" },
        },
        inventory_items: [
          { item_id: "item_sword", name: "Geschwungenes Langschwert", stack: 1, rarity: "rare", slot: "weapon" },
          { item_id: "item_ration", name: "Reiseration", stack: 3, rarity: "common", slot: "" },
          { item_id: "item_seal", name: "Siegel der Grauen Hand", stack: 1, rarity: "common", slot: "quest" },
          { item_id: "item_ring", name: "Verfluchter Ring", stack: 1, rarity: "common", slot: "ring_1", cursed: true },
        ],
      },
    },
  } as unknown as CharacterSheetResponse;
}

describe("deriveActorDockView gear mapping", () => {
  it("shows equipped items and hides empty slots", () => {
    const view = deriveActorDockView(createCampaignFixture(), "aria", sheetWithGear());
    expect(view.equipment).toEqual([{ slot: "Waffe", name: "Geschwungenes Langschwert" }]);
  });

  it("lists rare, quest and cursed items as important, hides plain commons", () => {
    const view = deriveActorDockView(createCampaignFixture(), "aria", sheetWithGear());
    const names = view.items.map((item) => item.name);
    expect(names).toContain("Geschwungenes Langschwert");
    expect(names).toContain("Siegel der Grauen Hand");
    expect(names).toContain("Verfluchter Ring");
    expect(names).not.toContain("Reiseration");
  });
});

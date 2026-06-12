import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import { deriveSceneAtmosphere } from "./sceneAtmosphere";

describe("deriveSceneAtmosphere", () => {
  it("builds a narrative sentence from location, time and weather", () => {
    const campaign = createCampaignFixture({
      state: {
        scenes: {
          scene_square: { name: "Market Square", location: "Hafenviertel von Karthen", mood: "unheimlich" },
        },
      },
      world_time: { day: 1, time_of_day: "night", weather: "feiner Nieselregen" },
    });

    const result = deriveSceneAtmosphere(campaign, "Market Square");
    expect(result.name).toBe("Market Square");
    expect(result.text).toBe(
      "Der Schauplatz liegt in Hafenviertel von Karthen. Feiner Nieselregen hängt in tiefer Nacht über der Szene. Die Stimmung wirkt unheimlich.",
    );
  });

  it("prefers an existing scene description over the constructed location sentence", () => {
    const campaign = createCampaignFixture({
      state: {
        scenes: {
          scene_square: { name: "Market Square", description: "Kalter Nebel liegt über den Ständen.", location: "Karthen" },
        },
      },
    });

    const result = deriveSceneAtmosphere(campaign, "Market Square");
    expect(result.text).toContain("Kalter Nebel liegt über den Ständen.");
    expect(result.text).not.toContain("Der Schauplatz liegt");
  });

  it("never falls back to debug strings when nothing is known", () => {
    const campaign = createCampaignFixture({
      state: { scenes: {} },
      world_time: { day: 1, time_of_day: "", weather: "" },
      party_overview: [],
    });

    const result = deriveSceneAtmosphere(campaign, "");
    expect(result.name).toBe("Unbekannter Schauplatz");
    expect(result.text).toBe(
      "Die genaue Lage ist noch nicht vollständig geklärt, aber die Szene wirkt dunkel, still und angespannt.",
    );
    expect(result.text).not.toMatch(/unbekannt[^,]*Wetter|Wetter unbekannt|Aktueller Schauplatz/);
  });

  it("uses the time of day alone when no weather exists", () => {
    const campaign = createCampaignFixture({
      world_time: { day: 1, time_of_day: "dawn", weather: "" },
    });

    const result = deriveSceneAtmosphere(campaign, "Market Square");
    expect(result.text).toContain("Die Szene liegt im ersten Morgengrauen.");
  });
});

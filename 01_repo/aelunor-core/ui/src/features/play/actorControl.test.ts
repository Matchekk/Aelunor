import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import { canControlActor, controllableActorIds } from "./actorControl";

describe("canControlActor", () => {
  it("allows only the viewer's own claimed character by default", () => {
    const campaign = createCampaignFixture();
    expect(canControlActor(campaign, "aria")).toBe(true);
    expect(canControlActor(campaign, "brann")).toBe(false);
    expect(canControlActor(campaign, "")).toBe(false);
    expect(canControlActor(campaign, null)).toBe(false);
  });

  it("allows a foreign character only with an explicit control grant", () => {
    const campaign = createCampaignFixture({
      state: {
        characters: {
          brann: { control_granted_to: ["player-host"] },
        },
      },
    });
    expect(canControlActor(campaign, "brann")).toBe(true);
  });

  it("lists only controllable party members", () => {
    const campaign = createCampaignFixture();
    expect(controllableActorIds(campaign)).toEqual(["aria"]);
  });
});

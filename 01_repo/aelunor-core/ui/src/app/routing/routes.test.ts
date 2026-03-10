import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import { normalizePlayRouteState, parseV1RouteIntent, serializePlayRouteState } from "./routes";

describe("parseV1RouteIntent", () => {
  it("parses the root and hub routes", () => {
    expect(parseV1RouteIntent("/v1")).toEqual({
      kind: "root",
      campaign_id: null,
      workspace: null,
    });

    expect(parseV1RouteIntent("/v1/hub")).toEqual({
      kind: "hub",
      campaign_id: null,
      workspace: null,
    });
  });

  it("parses campaign workspace routes", () => {
    expect(parseV1RouteIntent("/v1/campaign/cmp_123/play")).toEqual({
      kind: "campaign",
      campaign_id: "cmp_123",
      workspace: "play",
    });
  });

  it("rejects unknown routes", () => {
    expect(parseV1RouteIntent("/v1/campaign/cmp_123/unknown")).toEqual({
      kind: "unknown",
      campaign_id: null,
      workspace: null,
    });
  });
});

describe("normalizePlayRouteState", () => {
  it("keeps a valid scene query and normalizes friendly board ids", () => {
    const campaign = createCampaignFixture();

    expect(normalizePlayRouteState(campaign, "?scene=scene_square&boards=story_cards")).toEqual({
      scene_id: "scene_square",
      boards_tab: "cards",
      drawer: null,
      context_open: false,
    });
  });

  it("drops invalid scene ids and prioritizes boards over other surfaces", () => {
    const campaign = createCampaignFixture();

    expect(normalizePlayRouteState(campaign, "?scene=missing&boards=session&drawer=character&slot=aria&context=1")).toEqual({
      scene_id: "all",
      boards_tab: "session",
      drawer: null,
      context_open: false,
    });
  });

  it("reconstructs a canonical search string for drawers", () => {
    const campaign = createCampaignFixture({
      state: {
        world: {
          races: {
            race_aurin: { name: "Aurin" },
          },
          beast_types: {},
        },
      },
    });

    const routeState = normalizePlayRouteState(campaign, "?scene=scene_square&drawer=codex&codex=race_aurin");
    expect(routeState).toEqual({
      scene_id: "scene_square",
      boards_tab: null,
      drawer: {
        drawer_type: "codex",
        entity_id: "race_aurin",
        codex_kind: "race",
      },
      context_open: false,
    });

    expect(serializePlayRouteState(routeState)).toBe("?scene=scene_square&drawer=codex&codex=race_aurin");
  });
});


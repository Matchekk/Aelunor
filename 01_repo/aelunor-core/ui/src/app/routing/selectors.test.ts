import { describe, expect, it } from "vitest";

import { createCampaignFixture } from "../../test/campaignFixture";
import { deriveRouteIntentResolution, deriveRouteRenderState } from "./selectors";

describe("deriveRouteRenderState", () => {
  it("routes to claim when no slot is claimed", () => {
    const campaign = createCampaignFixture({
      viewer_context: {
        player_id: "player-host",
        display_name: "Host",
        is_host: true,
        claimed_slot_id: null,
        claimed_character: null,
        phase: "active",
        needs_world_setup: false,
        needs_character_setup: false,
        pending_setup_question: null,
      },
    });

    expect(deriveRouteRenderState(campaign)).toEqual({
      workspace: "claim",
      canonical_workspace: "claim",
      show_setup_overlay: false,
    });
  });

  it("keeps claim workspace mounted but shows setup overlay when setup still blocks", () => {
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
        pending_setup_question: {
          question: {
            question_id: "q_name",
            label: "Name",
            type: "text",
            required: true,
            options: [],
            option_entries: [],
            allow_other: false,
            ai_copy: "Choose a name.",
            existing_answer: null,
          },
          progress: {
            answered: 0,
            total: 1,
            step: 1,
          },
        },
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
            question_id: "q_name",
            label: "Name",
            type: "text",
            required: true,
            options: [],
            option_entries: [],
            allow_other: false,
            ai_copy: "Choose a name.",
            existing_answer: null,
          },
          progress: {
            answered: 0,
            total: 1,
            step: 1,
          },
        },
      },
    });

    expect(deriveRouteRenderState(campaign)).toEqual({
      workspace: "claim",
      canonical_workspace: "setup",
      show_setup_overlay: true,
    });
  });

  it("routes directly to play once claim and setup are complete", () => {
    const campaign = createCampaignFixture();

    expect(deriveRouteRenderState(campaign)).toEqual({
      workspace: "play",
      canonical_workspace: "play",
      show_setup_overlay: false,
    });
  });

  it("marks mismatched route intent for redirect to canonical workspace", () => {
    const campaign = createCampaignFixture();

    expect(
      deriveRouteIntentResolution(
        {
          kind: "campaign",
          campaign_id: campaign.campaign_meta.campaign_id,
          workspace: "claim",
        },
        campaign,
      ),
    ).toEqual({
      should_redirect: true,
      target_workspace: "play",
    });
  });
});

import { describe, expect, it } from "vitest";

import {
  DEFAULT_RULE_PROFILE_ID,
  buildRuleProfileRuntimeState,
  describeRuleProfileForSetup,
  findRuleProfileDefinition,
  listMvpRuleProfiles,
} from "./ruleProfiles";

describe("ruleProfiles", () => {
  it("falls back to the default cinematic profile for unknown input", () => {
    const definition = findRuleProfileDefinition("unknown_profile");

    expect(definition.id).toBe(DEFAULT_RULE_PROFILE_ID);
    expect(definition.resolution_mode).toBe("ai_judgement");
    expect(definition.dice_formula).toBeNull();
  });

  it("builds a runtime state from a d20 profile", () => {
    const runtimeState = buildRuleProfileRuntimeState("d20_fantasy");

    expect(runtimeState).toEqual({
      profile_id: "d20_fantasy",
      resolution_mode: "dice_check",
      dice_formula: "1d20",
      player_visible_rolls: true,
    });
  });

  it("keeps the first MVP profile set focused", () => {
    const mvpProfileIds = listMvpRuleProfiles().map((definition) => definition.id);

    expect(mvpProfileIds).toEqual(["cinematic_ai", "simple_d6", "d20_fantasy"]);
  });

  it("describes setup profiles with dice visibility", () => {
    expect(describeRuleProfileForSetup("simple_d6")).toContain("Würfel: 1d6");
    expect(describeRuleProfileForSetup("cinematic_ai")).toContain("Keine sichtbaren Würfel");
  });
});

import { describe, expect, it } from "vitest";

import { derivePresenceKindForContext, deriveSetupPresenceKind } from "./activity";

describe("presence activity helpers", () => {
  it("maps setup modes to stable presence activity kinds", () => {
    expect(deriveSetupPresenceKind("world")).toBe("building_world");
    expect(deriveSetupPresenceKind("character")).toBe("building_character");
  });

  it("maps all supported UI contexts to backend presence kinds", () => {
    expect(derivePresenceKindForContext("typing")).toBe("typing_turn");
    expect(derivePresenceKindForContext("world_setup")).toBe("building_world");
    expect(derivePresenceKindForContext("character_setup")).toBe("building_character");
    expect(derivePresenceKindForContext("turn_edit")).toBe("editing_turn");
    expect(derivePresenceKindForContext("slot_claim")).toBe("claiming_slot");
  });
});

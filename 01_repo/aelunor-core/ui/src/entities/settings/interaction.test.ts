import { describe, expect, it } from "vitest";

import { resolveInitialComposerMode, shouldOpenTimelineDetails } from "./interaction";

describe("settings interaction helpers", () => {
  it("maps composer preference to a valid initial mode", () => {
    expect(resolveInitialComposerMode("do")).toBe("do");
    expect(resolveInitialComposerMode("say")).toBe("say");
    expect(resolveInitialComposerMode("story")).toBe("story");
  });

  it("resolves timeline details default state", () => {
    expect(shouldOpenTimelineDetails("collapsed")).toBe(false);
    expect(shouldOpenTimelineDetails("expanded")).toBe(true);
  });
});

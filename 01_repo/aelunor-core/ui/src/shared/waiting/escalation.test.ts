import { describe, expect, it } from "vitest";

import { createWaitingPresentation, deriveEffectiveScope, deriveWaitingStage, pickPrimaryWaiting } from "./escalation";
import type { WaitingSignal } from "./model";

function createSignal(partial: Partial<WaitingSignal>): WaitingSignal {
  return {
    key: partial.key ?? "signal",
    context: partial.context ?? "story_turn",
    scope: partial.scope ?? "inline",
    blocking_level: partial.blocking_level ?? "non_blocking",
    surface_target: partial.surface_target ?? "timeline",
    message_override: partial.message_override ?? null,
    detail_override: partial.detail_override ?? null,
    started_at: partial.started_at ?? 0,
  };
}

describe("waiting escalation", () => {
  it("derives inline stage by elapsed time", () => {
    expect(deriveWaitingStage("inline", 200)).toBe(0);
    expect(deriveWaitingStage("inline", 1800)).toBe(1);
    expect(deriveWaitingStage("inline", 6200)).toBe(2);
    expect(deriveWaitingStage("inline", 15000)).toBe(3);
  });

  it("keeps story_turn waiting inline even on long durations", () => {
    const signal = createSignal({
      context: "story_turn",
      scope: "inline",
      blocking_level: "local_blocking",
    });
    expect(deriveEffectiveScope(signal, 3)).toBe("inline");
  });

  it("promotes panel loading from inline to surface on long blocking waits", () => {
    const signal = createSignal({
      context: "panel_load",
      scope: "inline",
      blocking_level: "local_blocking",
      surface_target: "drawer",
    });
    expect(deriveEffectiveScope(signal, 2)).toBe("surface");
  });

  it("picks stronger scoped waiting when multiple signals are active", () => {
    const now = 10000;
    const inlineSignal = createSignal({
      key: "inline",
      context: "context_query",
      scope: "inline",
      blocking_level: "local_blocking",
      surface_target: "composer",
      started_at: now - 9000,
    });
    const surfaceSignal = createSignal({
      key: "surface",
      context: "setup_step",
      scope: "surface",
      blocking_level: "major_blocking",
      surface_target: "composer",
      started_at: now - 2000,
    });

    const picked = pickPrimaryWaiting([inlineSignal, surfaceSignal], now, "surface");
    expect(picked?.signal.key).toBe("surface");
  });

  it("creates presentation copy with overrides when provided", () => {
    const signal = createSignal({
      context: "campaign_open",
      scope: "full",
      blocking_level: "full_blocking",
      surface_target: "route_gate",
      message_override: "Eigener Titel",
      detail_override: "Eigene Details",
      started_at: 1000,
    });

    const presentation = createWaitingPresentation(signal, 2200);
    expect(presentation.heading).toBe("Eigener Titel");
    expect(presentation.detail).toBe("Eigene Details");
  });
});

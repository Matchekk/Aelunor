import { deriveWaitingCopy } from "./messages";
import {
  WAITING_BLOCKING_RANK,
  WAITING_SCOPE_RANK,
  type WaitingPresentation,
  type WaitingScope,
  type WaitingSignal,
  type WaitingContextId,
} from "./model";

const STAGE_THRESHOLDS_MS: Record<WaitingScope, readonly [number, number, number]> = {
  inline: [1400, 5200, 12000],
  surface: [1200, 4500, 10000],
  section: [900, 3600, 9000],
  full: [700, 3000, 8000],
};

const MAX_SCOPE_BY_CONTEXT: Record<WaitingContextId, WaitingScope> = {
  story_turn: "inline",
  context_query: "surface",
  campaign_open: "full",
  campaign_create: "section",
  campaign_join: "section",
  session_resume: "section",
  setup_step: "section",
  setup_random: "section",
  setup_waiting_host: "section",
  scene_switch: "section",
  panel_load: "surface",
};

function clampScope(candidate: WaitingScope, max_scope: WaitingScope): WaitingScope {
  if (WAITING_SCOPE_RANK[candidate] <= WAITING_SCOPE_RANK[max_scope]) {
    return candidate;
  }
  return max_scope;
}

export function deriveWaitingStage(scope: WaitingScope, elapsed_ms: number): 0 | 1 | 2 | 3 {
  const [t1, t2, t3] = STAGE_THRESHOLDS_MS[scope];
  if (elapsed_ms < t1) {
    return 0;
  }
  if (elapsed_ms < t2) {
    return 1;
  }
  if (elapsed_ms < t3) {
    return 2;
  }
  return 3;
}

export function deriveEffectiveScope(signal: WaitingSignal, stage: 0 | 1 | 2 | 3): WaitingScope {
  let scope = signal.scope;

  if (stage >= 2 && scope === "inline" && signal.blocking_level !== "non_blocking") {
    scope = "surface";
  }

  if (
    stage >= 3 &&
    scope === "surface" &&
    (signal.blocking_level === "major_blocking" || signal.blocking_level === "full_blocking")
  ) {
    scope = "section";
  }

  if (stage >= 3 && scope === "section" && signal.blocking_level === "full_blocking") {
    scope = "full";
  }

  return clampScope(scope, MAX_SCOPE_BY_CONTEXT[signal.context]);
}

export function createWaitingPresentation(signal: WaitingSignal, now: number): WaitingPresentation {
  const elapsed_ms = Math.max(0, now - signal.started_at);
  const stage = deriveWaitingStage(signal.scope, elapsed_ms);
  const effective_scope = deriveEffectiveScope(signal, stage);
  const copy = deriveWaitingCopy(signal.context, stage, signal.message_override, signal.detail_override);

  return {
    signal,
    elapsed_ms,
    stage,
    effective_scope,
    heading: copy.heading,
    detail: copy.detail,
  };
}

export function pickPrimaryWaiting(
  signals: WaitingSignal[],
  now: number,
  min_scope: WaitingScope,
  max_scope: WaitingScope | null = null,
): WaitingPresentation | null {
  const min_rank = WAITING_SCOPE_RANK[min_scope];
  const max_rank = max_scope ? WAITING_SCOPE_RANK[max_scope] : Number.POSITIVE_INFINITY;
  const candidates = signals
    .map((signal) => createWaitingPresentation(signal, now))
    .filter((presentation) => {
      const rank = WAITING_SCOPE_RANK[presentation.effective_scope];
      return rank >= min_rank && rank <= max_rank;
    });

  if (candidates.length === 0) {
    return null;
  }

  candidates.sort((left, right) => {
    const leftScopeRank = WAITING_SCOPE_RANK[left.effective_scope];
    const rightScopeRank = WAITING_SCOPE_RANK[right.effective_scope];
    if (leftScopeRank !== rightScopeRank) {
      return rightScopeRank - leftScopeRank;
    }

    const leftBlockingRank = WAITING_BLOCKING_RANK[left.signal.blocking_level];
    const rightBlockingRank = WAITING_BLOCKING_RANK[right.signal.blocking_level];
    if (leftBlockingRank !== rightBlockingRank) {
      return rightBlockingRank - leftBlockingRank;
    }

    if (left.stage !== right.stage) {
      return right.stage - left.stage;
    }

    return right.elapsed_ms - left.elapsed_ms;
  });

  return candidates[0] ?? null;
}

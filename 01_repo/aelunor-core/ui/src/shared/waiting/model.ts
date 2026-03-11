export type WaitingContextId =
  | "story_turn"
  | "context_query"
  | "campaign_open"
  | "campaign_create"
  | "campaign_join"
  | "session_resume"
  | "setup_step"
  | "setup_random"
  | "setup_waiting_host"
  | "scene_switch"
  | "panel_load";

export type WaitingScope = "inline" | "surface" | "section" | "full";

export type WaitingBlockingLevel = "non_blocking" | "local_blocking" | "major_blocking" | "full_blocking";

export type WaitingSurfaceTarget =
  | "timeline"
  | "composer"
  | "hub_create"
  | "hub_join"
  | "hub_resume"
  | "setup_question"
  | "setup_side"
  | "setup_overlay"
  | "drawer"
  | "route_gate";

export interface WaitingSignal {
  key: string;
  context: WaitingContextId;
  scope: WaitingScope;
  blocking_level: WaitingBlockingLevel;
  surface_target: WaitingSurfaceTarget;
  message_override: string | null;
  detail_override: string | null;
  started_at: number;
}

export interface WaitingSignalInput {
  key: string;
  context: WaitingContextId;
  scope: WaitingScope;
  blocking_level: WaitingBlockingLevel;
  surface_target: WaitingSurfaceTarget;
  message_override?: string | null;
  detail_override?: string | null;
}

export interface WaitingPresentation {
  signal: WaitingSignal;
  elapsed_ms: number;
  stage: 0 | 1 | 2 | 3;
  effective_scope: WaitingScope;
  heading: string;
  detail: string;
}

export const WAITING_SCOPE_RANK: Record<WaitingScope, number> = {
  inline: 1,
  surface: 2,
  section: 3,
  full: 4,
};

export const WAITING_BLOCKING_RANK: Record<WaitingBlockingLevel, number> = {
  non_blocking: 1,
  local_blocking: 2,
  major_blocking: 3,
  full_blocking: 4,
};

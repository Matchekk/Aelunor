import type { TimelineEntry } from "./selectors";

export const INITIAL_TIMELINE_WINDOW = 48;
export const TIMELINE_WINDOW_STEP = 32;

export interface TimelineWindowState {
  visible_count: number;
  hidden_count: number;
  can_load_more: boolean;
}

function clampCount(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.max(min, Math.min(max, Math.floor(value)));
}

export function deriveInitialVisibleCount(total_count: number): number {
  if (total_count <= 0) {
    return 0;
  }
  return Math.min(total_count, INITIAL_TIMELINE_WINDOW);
}

export function deriveTimelineWindow(total_count: number, requested_visible_count: number): TimelineWindowState {
  const safeTotal = Math.max(0, Math.floor(total_count));
  const visible_count = safeTotal === 0 ? 0 : clampCount(requested_visible_count, 1, safeTotal);
  return {
    visible_count,
    hidden_count: Math.max(0, safeTotal - visible_count),
    can_load_more: visible_count < safeTotal,
  };
}

export function deriveNextVisibleCount(params: {
  previous_total_count: number;
  next_total_count: number;
  current_visible_count: number;
  scene_changed: boolean;
}): number {
  const previous_total_count = Math.max(0, Math.floor(params.previous_total_count));
  const next_total_count = Math.max(0, Math.floor(params.next_total_count));

  if (next_total_count === 0) {
    return 0;
  }

  if (params.scene_changed || params.current_visible_count <= 0) {
    return deriveInitialVisibleCount(next_total_count);
  }

  if (next_total_count <= params.current_visible_count) {
    return next_total_count;
  }

  const growth = Math.max(0, next_total_count - previous_total_count);
  if (growth > 0) {
    return Math.min(next_total_count, params.current_visible_count + growth);
  }

  return clampCount(params.current_visible_count, 1, next_total_count);
}

export function deriveRenderedTimelineEntries(entries: TimelineEntry[], visible_count: number): TimelineEntry[] {
  if (visible_count <= 0) {
    return [];
  }
  return entries.slice(0, visible_count);
}

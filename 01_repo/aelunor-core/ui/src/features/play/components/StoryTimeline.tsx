import { memo, useEffect, useMemo, useRef, useState } from "react";

import type { TimelineEntry } from "../selectors";
import { deriveTurnDeltaRows, deriveTurnLead, deriveTurnOutcome, formatTimelineTimestamp } from "../selectors";
import {
  deriveInitialVisibleCount,
  deriveNextVisibleCount,
  deriveRenderedTimelineEntries,
  deriveTimelineWindow,
  TIMELINE_WINDOW_STEP,
} from "../timelineWindow";

interface StoryTimelineProps {
  entries: TimelineEntry[];
  character_sheet_slots: string[];
  selected_scene_id: string;
  selected_scene_name: string | null;
  on_open_character: (slot_id: string, tab_id?: string) => void;
}

interface TimelineItemProps {
  entry: TimelineEntry;
  character_sheet_slots: string[];
  on_open_character: (slot_id: string, tab_id?: string) => void;
}

const TimelineItem = memo(function TimelineItem({ entry, character_sheet_slots, on_open_character }: TimelineItemProps) {
  const deltaRows = useMemo(() => deriveTurnDeltaRows(entry), [entry]);

  return (
    <li className="timeline-item story-turn-card">
      <div className="timeline-item-head">
        <div className="timeline-item-title">
          <strong>Turn {entry.turn_number ?? "?"}</strong>
          <span className="timeline-mode-pill">{entry.mode}</span>
          {entry.scene_name ? <span className="timeline-scene-pill">{entry.scene_name}</span> : null}
        </div>
        <span>{formatTimelineTimestamp(entry.created_at)}</span>
      </div>
      <div className="timeline-item-actor story-turn-meta">
        {character_sheet_slots.includes(entry.actor_id) ? (
          <button type="button" className="timeline-actor-button" onClick={() => on_open_character(entry.actor_id)}>
            {entry.actor_display}
          </button>
        ) : (
          entry.actor_display
        )}
      </div>
      <p className="timeline-item-input story-turn-lead">{deriveTurnLead(entry)}</p>
      <p className="story-turn-text">{deriveTurnOutcome(entry)}</p>
      {deltaRows.length > 0 ? (
        <details className="timeline-delta-block">
          <summary>
            <span>State delta</span>
            <small>{entry.patch_summary_label ?? `${deltaRows.length} changes`}</small>
          </summary>
          <ul>
            {deltaRows.map((row) => (
              <li key={row.key}>
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </li>
  );
});

export const StoryTimeline = memo(function StoryTimeline({
  entries,
  character_sheet_slots,
  selected_scene_id,
  selected_scene_name,
  on_open_character,
}: StoryTimelineProps) {
  const [visibleCount, setVisibleCount] = useState(() => deriveInitialVisibleCount(entries.length));
  const previousSceneIdRef = useRef(selected_scene_id);
  const previousTotalCountRef = useRef(entries.length);

  useEffect(() => {
    const scene_changed = previousSceneIdRef.current !== selected_scene_id;
    setVisibleCount((current) =>
      deriveNextVisibleCount({
        previous_total_count: previousTotalCountRef.current,
        next_total_count: entries.length,
        current_visible_count: current,
        scene_changed,
      }),
    );
    previousSceneIdRef.current = selected_scene_id;
    previousTotalCountRef.current = entries.length;
  }, [entries.length, selected_scene_id]);

  const windowState = useMemo(() => deriveTimelineWindow(entries.length, visibleCount), [entries.length, visibleCount]);
  const renderedEntries = useMemo(
    () => deriveRenderedTimelineEntries(entries, windowState.visible_count),
    [entries, windowState.visible_count],
  );

  return (
    <section className="story-timeline panel timeline-panel">
      <div className="v1-panel-head timeline-head">
        <h2 className="panelTitle">Geschichte</h2>
        <span>{selected_scene_name ? `${selected_scene_name} • ${entries.length} turns` : `${entries.length} turns`}</span>
      </div>
      {windowState.hidden_count > 0 ? (
        <div className="timeline-window-status">
          <span className="status-muted">
            Showing the latest {windowState.visible_count} turns. {windowState.hidden_count} older turns stay collapsed
            until requested.
          </span>
        </div>
      ) : null}
      {entries.length === 0 ? (
        <div className="timeline-empty">
          <p className="status-muted">{selected_scene_name ? "No turns are visible for this scene yet." : "No active story turns yet."}</p>
          <p className="status-muted">
            {selected_scene_name
              ? "Switch back to All scenes to include turns without explicit scene markers."
              : "Once the backend generates or advances turns, they will appear here."}
          </p>
        </div>
      ) : (
        <ol className="timeline-list">
          {renderedEntries.map((entry) => (
            <TimelineItem
              key={entry.turn_id}
              entry={entry}
              character_sheet_slots={character_sheet_slots}
              on_open_character={on_open_character}
            />
          ))}
        </ol>
      )}
      {windowState.can_load_more ? (
        <div className="timeline-window-actions">
          <button
            type="button"
            onClick={() => {
              setVisibleCount((current) => Math.min(entries.length, current + TIMELINE_WINDOW_STEP));
            }}
          >
            Load {Math.min(TIMELINE_WINDOW_STEP, windowState.hidden_count)} older turn
            {Math.min(TIMELINE_WINDOW_STEP, windowState.hidden_count) === 1 ? "" : "s"}
          </button>
          <button
            type="button"
            onClick={() => {
              setVisibleCount(entries.length);
            }}
          >
            Show all visible turns
          </button>
        </div>
      ) : null}
    </section>
  );
});

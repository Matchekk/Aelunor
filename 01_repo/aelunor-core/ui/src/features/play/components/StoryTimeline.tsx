import { memo, useEffect, useMemo, useRef, useState } from "react";

import { shouldOpenTimelineDetails } from "../../../entities/settings/interaction";
import { useUserSettingsStore } from "../../../entities/settings/store";
import type { TimelineEntry } from "../selectors";
import { deriveTurnDeltaRows, deriveTurnLead, deriveTurnOutcome, formatTimelineTimestamp } from "../selectors";
import { WaitingInline } from "../../../shared/waiting/components";
import type { SceneFilterId, SceneOption } from "../../scenes/selectors";
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
  selected_scene_id: SceneFilterId;
  selected_scene_name: string | null;
  scene_options: SceneOption[];
  is_preplay: boolean;
  can_continue_turn: boolean;
  turn_actions_pending: boolean;
  turn_action_pending_id: string | null;
  turn_action_error: string | null;
  on_scene_change: (scene_id: SceneFilterId) => void;
  on_open_character: (slot_id: string, tab_id?: string) => void;
  on_edit_turn: (entry: TimelineEntry) => void;
  on_undo_turn: (turn_id: string) => void;
  on_retry_turn: (turn_id: string) => void;
  on_continue_turn: () => void;
}

interface TimelineItemProps {
  entry: TimelineEntry;
  is_latest_turn: boolean;
  character_sheet_slots: string[];
  details_open_by_default: boolean;
  can_continue_turn: boolean;
  turn_actions_pending: boolean;
  turn_action_pending_id: string | null;
  on_open_character: (slot_id: string, tab_id?: string) => void;
  on_edit_turn: (entry: TimelineEntry) => void;
  on_undo_turn: (turn_id: string) => void;
  on_retry_turn: (turn_id: string) => void;
  on_continue_turn: () => void;
}

const TimelineItem = memo(function TimelineItem({
  entry,
  is_latest_turn,
  character_sheet_slots,
  details_open_by_default,
  can_continue_turn,
  turn_actions_pending,
  turn_action_pending_id,
  on_open_character,
  on_edit_turn,
  on_undo_turn,
  on_retry_turn,
  on_continue_turn,
}: TimelineItemProps) {
  const deltaRows = useMemo(() => deriveTurnDeltaRows(entry), [entry]);
  const detailsProps = details_open_by_default ? { open: true } : {};
  const isPendingTurnAction = Boolean(turn_action_pending_id && turn_action_pending_id === entry.turn_id);
  const canRenderTurnActions = is_latest_turn && (entry.can_edit || entry.can_undo || entry.can_retry || can_continue_turn);

  return (
    <li className="timeline-item story-turn-card">
      <div className="timeline-item-head">
        <div className="timeline-item-title">
          <strong>Zug {entry.turn_number ?? "?"}</strong>
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
        <details
          key={`${entry.turn_id}-${details_open_by_default ? "expanded" : "collapsed"}`}
          className="timeline-delta-block"
          {...detailsProps}
        >
          <summary>
            <span>Änderungen</span>
            <small>{entry.patch_summary_label ?? `${deltaRows.length} Einträge`}</small>
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
      {canRenderTurnActions ? (
        <div className="timeline-turn-actions">
          {entry.can_edit ? (
            <button
              type="button"
              onClick={() => on_edit_turn(entry)}
              disabled={turn_actions_pending}
            >
              {isPendingTurnAction ? "Bearbeiten..." : "Bearbeiten"}
            </button>
          ) : null}
          {entry.can_undo ? (
            <button
              type="button"
              onClick={() => on_undo_turn(entry.turn_id)}
              disabled={turn_actions_pending}
            >
              {isPendingTurnAction ? "Zurücknehmen..." : "Zurücknehmen"}
            </button>
          ) : null}
          {entry.can_retry ? (
            <button
              type="button"
              onClick={() => on_retry_turn(entry.turn_id)}
              disabled={turn_actions_pending}
            >
              {isPendingTurnAction ? "Erneut versuchen..." : "Erneut versuchen"}
            </button>
          ) : null}
          {can_continue_turn ? (
            <button type="button" className="is-primary" onClick={on_continue_turn} disabled={turn_actions_pending}>
              Weiter
            </button>
          ) : null}
        </div>
      ) : null}
    </li>
  );
});

export const StoryTimeline = memo(function StoryTimeline({
  entries,
  character_sheet_slots,
  selected_scene_id,
  selected_scene_name,
  scene_options,
  is_preplay,
  can_continue_turn,
  turn_actions_pending,
  turn_action_pending_id,
  turn_action_error,
  on_scene_change,
  on_open_character,
  on_edit_turn,
  on_undo_turn,
  on_retry_turn,
  on_continue_turn,
}: StoryTimelineProps) {
  const autoScroll = useUserSettingsStore((state) => state.interaction.auto_scroll);
  const detailsOpenByDefault = useUserSettingsStore((state) =>
    shouldOpenTimelineDetails(state.interaction.timeline_detail_default),
  );
  const [visibleCount, setVisibleCount] = useState(() => deriveInitialVisibleCount(entries.length));
  const previousSceneIdRef = useRef(selected_scene_id);
  const previousTotalCountRef = useRef(entries.length);
  const previousLatestTurnRef = useRef(entries[0]?.turn_id ?? null);
  const timelineRef = useRef<HTMLElement | null>(null);

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

  useEffect(() => {
    const latestTurnId = entries[0]?.turn_id ?? null;
    if (!autoScroll || !latestTurnId) {
      previousLatestTurnRef.current = latestTurnId;
      return;
    }

    if (previousLatestTurnRef.current && previousLatestTurnRef.current !== latestTurnId) {
      timelineRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }

    previousLatestTurnRef.current = latestTurnId;
  }, [autoScroll, entries]);

  return (
    <section ref={timelineRef} className="story-timeline panel timeline-panel">
      <div className="v1-panel-head timeline-head">
        <h2 className="panelTitle">{is_preplay ? "Verlauf" : "Geschichte"}</h2>
        <span>{selected_scene_name ? `${selected_scene_name} • ${entries.length} Züge` : `${entries.length} Züge`}</span>
      </div>
      {scene_options.length > 1 ? (
        <div className="timeline-scene-switcher" role="tablist" aria-label="Szenenfilter">
          {scene_options.map((option) => (
            <button
              key={option.scene_id}
              type="button"
              className={option.scene_id === selected_scene_id ? "command-scene-chip is-active" : "command-scene-chip"}
              onClick={() => on_scene_change(option.scene_id)}
              aria-pressed={option.scene_id === selected_scene_id}
            >
              <span>{option.scene_name}</span>
              <small>{option.member_count}</small>
            </button>
          ))}
        </div>
      ) : null}
      <WaitingInline target="timeline" className="timeline-waiting-inline" />
      {turn_action_error ? <div className="session-feedback error">{turn_action_error}</div> : null}
      {windowState.hidden_count > 0 ? (
        <div className="timeline-window-status">
          <span className="status-muted">
            Zeige die neuesten {windowState.visible_count} Züge. {windowState.hidden_count} ältere Züge bleiben eingeklappt,
            bis du sie öffnest.
          </span>
        </div>
      ) : null}
      {entries.length === 0 ? (
        <div className="timeline-empty">
          <p className="status-muted">{selected_scene_name ? "Für diese Szene sind noch keine Züge sichtbar." : "Noch keine Story-Züge vorhanden."}</p>
          <p className="status-muted">
            {selected_scene_name
              ? "Wechsle zu „Alle Szenen“, um auch Einträge ohne Szenenmarker zu sehen."
              : "Sobald Züge entstehen oder fortgesetzt werden, erscheinen sie hier."}
          </p>
        </div>
      ) : (
        <ol className="timeline-list">
          {renderedEntries.map((entry) => (
            <TimelineItem
              key={entry.turn_id}
              entry={entry}
              is_latest_turn={entry.turn_id === entries[0]?.turn_id}
              character_sheet_slots={character_sheet_slots}
              details_open_by_default={detailsOpenByDefault}
              can_continue_turn={can_continue_turn && entry.turn_id === entries[0]?.turn_id}
              turn_actions_pending={turn_actions_pending}
              turn_action_pending_id={turn_action_pending_id}
              on_open_character={on_open_character}
              on_edit_turn={on_edit_turn}
              on_undo_turn={on_undo_turn}
              on_retry_turn={on_retry_turn}
              on_continue_turn={on_continue_turn}
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
            {Math.min(TIMELINE_WINDOW_STEP, windowState.hidden_count)} ältere Zug
            {Math.min(TIMELINE_WINDOW_STEP, windowState.hidden_count) === 1 ? "" : "e"} laden
          </button>
          <button
            type="button"
            onClick={() => {
              setVisibleCount(entries.length);
            }}
          >
            Alle sichtbaren Züge anzeigen
          </button>
        </div>
      ) : null}
    </section>
  );
});

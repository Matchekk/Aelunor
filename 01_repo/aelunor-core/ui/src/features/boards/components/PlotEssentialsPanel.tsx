import { useEffect, useState } from "react";

import type { PlotEssentialsBoard, PlotEssentialsPatchRequest } from "../../../shared/api/contracts";
import { formatBoardTimestamp } from "../selectors";

interface PlotEssentialsPanelProps {
  board: PlotEssentialsBoard;
  can_edit: boolean;
  pending: boolean;
  error_message: string | null;
  on_save: (payload: PlotEssentialsPatchRequest) => void;
}

export function PlotEssentialsPanel({ board, can_edit, pending, error_message, on_save }: PlotEssentialsPanelProps) {
  const [draft, setDraft] = useState<PlotEssentialsPatchRequest>(board);

  useEffect(() => {
    setDraft(board);
  }, [board]);

  return (
    <section className="boards-panel">
      <div className="v1-panel-head">
        <h2>Plot Essentials</h2>
        <span>{can_edit ? "Host editable" : "Read-only"}</span>
      </div>
      <div className="boards-form-grid">
        <label>
          Premise
          <textarea
            value={draft.premise ?? ""}
            readOnly={!can_edit}
            onChange={(event) => setDraft((prev) => ({ ...prev, premise: event.target.value }))}
          />
        </label>
        <label>
          Current Goal
          <textarea
            value={draft.current_goal ?? ""}
            readOnly={!can_edit}
            onChange={(event) => setDraft((prev) => ({ ...prev, current_goal: event.target.value }))}
          />
        </label>
        <label>
          Current Threat
          <textarea
            value={draft.current_threat ?? ""}
            readOnly={!can_edit}
            onChange={(event) => setDraft((prev) => ({ ...prev, current_threat: event.target.value }))}
          />
        </label>
        <label>
          Active Scene
          <textarea
            value={draft.active_scene ?? ""}
            readOnly={!can_edit}
            onChange={(event) => setDraft((prev) => ({ ...prev, active_scene: event.target.value }))}
          />
        </label>
        <label>
          Open Loops
          <textarea
            value={(draft.open_loops ?? []).join("\n")}
            readOnly={!can_edit}
            onChange={(event) =>
              setDraft((prev) => ({
                ...prev,
                open_loops: event.target.value
                  .split("\n")
                  .map((line) => line.trim())
                  .filter(Boolean),
              }))
            }
          />
        </label>
        <label>
          Tone
          <textarea
            value={draft.tone ?? ""}
            readOnly={!can_edit}
            onChange={(event) => setDraft((prev) => ({ ...prev, tone: event.target.value }))}
          />
        </label>
      </div>
      <div className="status-muted">Updated {formatBoardTimestamp(board.updated_at)}</div>
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
      {can_edit ? (
        <div className="session-inline-actions">
          <button type="button" onClick={() => on_save(draft)} disabled={pending}>
            {pending ? "Saving..." : "Save plot essentials"}
          </button>
        </div>
      ) : null}
    </section>
  );
}

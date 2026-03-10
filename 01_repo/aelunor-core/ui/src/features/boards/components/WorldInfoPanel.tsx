import { useState } from "react";

import type { WorldInfoCreateRequest, WorldInfoEntry } from "../../../shared/api/contracts";
import { deriveWorldInfoSubtitle, formatBoardTimestamp } from "../selectors";
import { WorldInfoEditor } from "./WorldInfoEditor";

interface WorldInfoPanelProps {
  entries: WorldInfoEntry[];
  can_edit: boolean;
  create_pending: boolean;
  patch_pending: boolean;
  error_message: string | null;
  on_create: (payload: WorldInfoCreateRequest) => void;
  on_patch: (entry_id: string, payload: WorldInfoCreateRequest) => void;
}

export function WorldInfoPanel({
  entries,
  can_edit,
  create_pending,
  patch_pending,
  error_message,
  on_create,
  on_patch,
}: WorldInfoPanelProps) {
  const [editing_entry_id, setEditingEntryId] = useState<string | null>(null);
  const editing_entry = entries.find((entry) => entry.entry_id === editing_entry_id) ?? null;

  return (
    <section className="boards-panel">
      <div className="v1-panel-head">
        <h2>World Info</h2>
        <span>{can_edit ? "Host editable" : "Read-only"}</span>
      </div>
      <p className="status-muted">
        Structured world facts stay editable for hosts here. Delete remains deferred until a backend delete path exists.
      </p>
      {can_edit ? (
        <WorldInfoEditor
          editing_entry={editing_entry}
          pending={create_pending || patch_pending}
          error_message={error_message}
          on_cancel={() => setEditingEntryId(null)}
          on_submit={(payload) => {
            if (editing_entry) {
              on_patch(editing_entry.entry_id, payload);
              return;
            }
            on_create(payload);
          }}
        />
      ) : null}
      <div className="boards-list">
        {entries.length > 0 ? (
          entries.map((entry) => (
            <article key={entry.entry_id} className="boards-list-item">
              <div className="v1-panel-head">
                <h2>{entry.title}</h2>
                <span>{formatBoardTimestamp(entry.updated_at)}</span>
              </div>
              <div className="status-muted">{deriveWorldInfoSubtitle(entry)}</div>
              <p>{entry.content}</p>
              {can_edit ? (
                <div className="session-inline-actions">
                  <button type="button" onClick={() => setEditingEntryId(entry.entry_id)}>
                    Edit
                  </button>
                </div>
              ) : null}
            </article>
          ))
        ) : (
          <div className="setup-empty-state">No world info entries exist yet.</div>
        )}
      </div>
    </section>
  );
}

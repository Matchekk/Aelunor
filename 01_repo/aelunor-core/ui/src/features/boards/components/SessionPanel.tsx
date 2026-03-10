import type { SessionBootstrap } from "../../../app/bootstrap/sessionStorage";
import type { SessionLibraryEntry } from "../../../shared/api/contracts";
import { formatBoardTimestamp } from "../selectors";
import { SessionDangerZone } from "./SessionDangerZone";

interface SessionPanelProps {
  campaign_title: string;
  updated_at: string;
  session: SessionBootstrap;
  local_entry: SessionLibraryEntry | null;
  can_edit: boolean;
  rename_value: string;
  rename_pending: boolean;
  delete_pending: boolean;
  error_message: string | null;
  delete_confirm_open: boolean;
  on_rename_change: (value: string) => void;
  on_save_rename: () => void;
  on_export_campaign: () => void;
  on_toggle_delete_confirm: (open: boolean) => void;
  on_delete_campaign: () => void;
  on_remove_local_entry: () => void;
}

export function SessionPanel({
  campaign_title,
  updated_at,
  session,
  local_entry,
  can_edit,
  rename_value,
  rename_pending,
  delete_pending,
  error_message,
  delete_confirm_open,
  on_rename_change,
  on_save_rename,
  on_export_campaign,
  on_toggle_delete_confirm,
  on_delete_campaign,
  on_remove_local_entry,
}: SessionPanelProps) {
  return (
    <section className="boards-panel">
      <div className="v1-panel-head">
        <h2>Session</h2>
        <span>{can_edit ? "Host controls" : "Read-only"}</span>
      </div>
      <div className="boards-form-grid">
        <label>
          Session title
          <input value={rename_value} readOnly={!can_edit} onChange={(event) => on_rename_change(event.target.value)} />
        </label>
        <div className="boards-session-meta">
          <div><strong>campaign_id:</strong> {session.campaign_id}</div>
          <div><strong>join_code:</strong> {session.join_code ?? "n/a"}</div>
          <div><strong>updated:</strong> {formatBoardTimestamp(updated_at)}</div>
          {local_entry ? <div><strong>local label:</strong> {local_entry.label}</div> : null}
          {!local_entry ? <div><strong>local session:</strong> not saved in library</div> : null}
        </div>
      </div>
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
      <div className="session-inline-actions">
        {can_edit ? (
          <button type="button" onClick={on_save_rename} disabled={rename_pending}>
            {rename_pending ? "Saving..." : "Save title"}
          </button>
        ) : null}
        <button type="button" onClick={on_export_campaign}>
          Export campaign JSON
        </button>
      </div>
      <SessionDangerZone
        can_delete_campaign={can_edit}
        has_local_entry={Boolean(local_entry)}
        delete_confirm_open={delete_confirm_open}
        delete_pending={delete_pending}
        on_toggle_confirm={on_toggle_delete_confirm}
        on_delete_campaign={on_delete_campaign}
        on_remove_local_entry={on_remove_local_entry}
      />
      <p className="status-muted">Current title: {campaign_title}</p>
    </section>
  );
}

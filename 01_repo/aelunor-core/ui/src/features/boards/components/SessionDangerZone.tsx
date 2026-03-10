interface SessionDangerZoneProps {
  can_delete_campaign: boolean;
  has_local_entry: boolean;
  delete_confirm_open: boolean;
  delete_pending: boolean;
  on_toggle_confirm: (open: boolean) => void;
  on_delete_campaign: () => void;
  on_remove_local_entry: () => void;
}

export function SessionDangerZone({
  can_delete_campaign,
  has_local_entry,
  delete_confirm_open,
  delete_pending,
  on_toggle_confirm,
  on_delete_campaign,
  on_remove_local_entry,
}: SessionDangerZoneProps) {
  return (
    <section className="boards-danger-zone">
      <div className="v1-panel-head">
        <h2>Danger Zone</h2>
      </div>
      <p className="status-muted">
        Local removal only forgets this browser session entry. Campaign delete is server-side and only available to the host.
      </p>
      <div className="session-inline-actions">
        {has_local_entry ? (
          <button type="button" onClick={on_remove_local_entry}>
            Remove local saved session
          </button>
        ) : null}
        {can_delete_campaign ? (
          <button type="button" onClick={() => on_toggle_confirm(true)} disabled={delete_pending}>
            Delete campaign
          </button>
        ) : null}
      </div>
      {delete_confirm_open ? (
        <div className="session-feedback error">
          <p>This permanently deletes the campaign on the server.</p>
          <div className="session-inline-actions">
            <button type="button" onClick={on_delete_campaign} disabled={delete_pending}>
              {delete_pending ? "Deleting..." : "Confirm delete"}
            </button>
            <button type="button" onClick={() => on_toggle_confirm(false)} disabled={delete_pending}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

interface ComposerStatusBarProps {
  actor: string | null;
  mode_label: string;
  helper_text: string;
  disabled_reason: string | null;
}

export function ComposerStatusBar({ actor, mode_label, helper_text, disabled_reason }: ComposerStatusBarProps) {
  return (
    <div className="composer-status-bar">
      <div className="composer-status-pills">
        <span className="status-pill">{mode_label}</span>
        <span className="status-pill">{actor ? `Actor ${actor}` : "No actor"}</span>
      </div>
      <p className="status-muted">{helper_text}</p>
      {disabled_reason ? <div className="session-feedback error">{disabled_reason}</div> : null}
    </div>
  );
}

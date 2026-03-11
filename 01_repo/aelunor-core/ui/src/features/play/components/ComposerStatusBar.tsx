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
        <span className="status-pill">Modus {mode_label}</span>
        <span className="status-pill">{actor ? `Akteur ${actor}` : "Kein aktiver Slot"}</span>
      </div>
      {!disabled_reason ? <p className="status-muted composer-mode-hint">{helper_text}</p> : null}
      {disabled_reason ? <div className="composer-inline-note">{disabled_reason}</div> : null}
    </div>
  );
}

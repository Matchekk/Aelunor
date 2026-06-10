interface ComposerStatusBarProps {
  helper_text: string;
  disabled_reason: string | null;
}

// Mode and actor live in the tabs and the actor dropdown; this bar only
// carries the human-readable hint or the blocking reason — no debug pills.
export function ComposerStatusBar({ helper_text, disabled_reason }: ComposerStatusBarProps) {
  return (
    <div className="composer-status-bar">
      {!disabled_reason ? <p className="status-muted composer-mode-hint">{helper_text}</p> : null}
      {disabled_reason ? <div className="composer-inline-note">{disabled_reason}</div> : null}
    </div>
  );
}

interface SetupActionBarProps {
  can_go_prev: boolean;
  can_skip: boolean;
  can_randomize: boolean;
  disabled: boolean;
  submit_pending: boolean;
  random_pending: boolean;
  apply_pending: boolean;
  blocking_hint: string | null;
  disabled_reason: string | null;
  submit_label: string;
  on_prev: () => void;
  on_skip: () => void;
  on_randomize: () => void;
  on_submit: () => void;
}

export function SetupActionBar({
  can_go_prev,
  can_skip,
  can_randomize,
  disabled,
  submit_pending,
  random_pending,
  apply_pending,
  blocking_hint,
  disabled_reason,
  submit_label,
  on_prev,
  on_skip,
  on_randomize,
  on_submit,
}: SetupActionBarProps) {
  const busy = submit_pending || random_pending || apply_pending;

  return (
    <footer className="v1-panel setup-action-bar">
      <div className="setup-action-copy">
        {blocking_hint ? <div className="session-feedback error">{blocking_hint}</div> : null}
        {!blocking_hint && disabled_reason ? <div className="status-muted">{disabled_reason}</div> : null}
      </div>
      <div className="setup-action-buttons">
        <button type="button" onClick={on_prev} disabled={!can_go_prev || busy}>
          Previous
        </button>
        <button type="button" onClick={on_skip} disabled={!can_skip || disabled || busy}>
          Skip
        </button>
        <button type="button" onClick={on_randomize} disabled={!can_randomize || disabled || busy}>
          {random_pending ? "Generating..." : "Randomize"}
        </button>
        <button type="button" onClick={on_submit} disabled={disabled || busy}>
          {submit_pending ? "Saving..." : submit_label}
        </button>
      </div>
    </footer>
  );
}

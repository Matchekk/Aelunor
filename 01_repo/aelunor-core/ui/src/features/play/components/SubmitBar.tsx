interface SubmitBarProps {
  submit_label: string;
  pending: boolean;
  disabled: boolean;
  error_message: string | null;
  on_submit: () => void;
}

export function SubmitBar({ submit_label, pending, disabled, error_message, on_submit }: SubmitBarProps) {
  return (
    <div className="submit-bar">
      <button type="button" onClick={on_submit} disabled={disabled || pending}>
        {pending ? "Wird gesendet..." : submit_label}
      </button>
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
    </div>
  );
}

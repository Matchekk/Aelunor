import type { SetupQuestionFieldProps } from "../questionRegistry";

export function SetupTextQuestion({ question, draft, disabled, on_change }: SetupQuestionFieldProps) {
  return (
    <label className="setup-field">
      <span>{question.label}</span>
      <input
        type="text"
        value={draft.value}
        disabled={disabled}
        onChange={(event) => {
          on_change({
            ...draft,
            value: event.target.value,
          });
        }}
      />
    </label>
  );
}

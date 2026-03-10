import type { SetupQuestionFieldProps } from "../questionRegistry";

export function SetupMultiSelectQuestion({ question, draft, disabled, on_change }: SetupQuestionFieldProps) {
  const options =
    question.option_entries.length > 0
      ? question.option_entries
      : question.options.map((option) => ({
          value: option,
          label: option,
          description: undefined as string | undefined,
        }));

  return (
    <div className="setup-field">
      <span>{question.label}</span>
      <div className="setup-choice-list">
        {options.map((option) => {
          const checked = draft.selected_values.includes(option.value);
          return (
            <label key={option.value} className={checked ? "setup-choice is-selected" : "setup-choice"}>
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={(event) => {
                  const selected_values = event.target.checked
                    ? [...draft.selected_values, option.value]
                    : draft.selected_values.filter((entry) => entry !== option.value);
                  on_change({
                    ...draft,
                    selected_values,
                  });
                }}
              />
              <span className="setup-choice-copy">
                <strong>{option.label}</strong>
                {option.description ? <small>{option.description}</small> : null}
              </span>
            </label>
          );
        })}
      </div>
      {question.allow_other ? (
        <label className="setup-field setup-field-inline">
          <span>{question.other_hint || "Additional entries, comma separated"}</span>
          <input
            type="text"
            value={draft.other_values_text}
            disabled={disabled}
            onChange={(event) => {
              on_change({
                ...draft,
                other_values_text: event.target.value,
              });
            }}
          />
        </label>
      ) : null}
    </div>
  );
}

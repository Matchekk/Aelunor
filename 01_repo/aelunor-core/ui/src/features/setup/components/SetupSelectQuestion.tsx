import type { SetupQuestionFieldProps } from "../questionRegistry";

export function SetupSelectQuestion({ question, draft, disabled, on_change }: SetupQuestionFieldProps) {
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
          const selected = draft.selected_value === option.value;
          return (
            <label key={option.value} className={selected ? "setup-choice is-selected" : "setup-choice"}>
              <input
                type="radio"
                name={`setup-select-${question.question_id}`}
                checked={selected}
                disabled={disabled}
                onChange={() => {
                  on_change({
                    ...draft,
                    selected_value: option.value,
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
        {question.allow_other ? (
          <label className={draft.selected_value === "__other__" ? "setup-choice is-selected" : "setup-choice"}>
            <input
              type="radio"
              name={`setup-select-${question.question_id}`}
              checked={draft.selected_value === "__other__"}
              disabled={disabled}
              onChange={() => {
                on_change({
                  ...draft,
                  selected_value: "__other__",
                });
              }}
            />
            <span className="setup-choice-copy">
              <strong>Other</strong>
              <small>{question.other_hint || "Describe a custom answer if nothing above fits."}</small>
            </span>
          </label>
        ) : null}
      </div>
      {question.allow_other ? (
        <label className="setup-field setup-field-inline">
          <span>{question.other_hint || "Custom answer"}</span>
          <input
            type="text"
            value={draft.other_text}
            disabled={disabled || draft.selected_value !== "__other__"}
            onChange={(event) => {
              on_change({
                ...draft,
                other_text: event.target.value,
              });
            }}
          />
        </label>
      ) : null}
    </div>
  );
}

import type { SetupQuestionFieldProps } from "../questionRegistry";

export function SetupBooleanQuestion({ question, draft, disabled, on_change }: SetupQuestionFieldProps) {
  return (
    <div className="setup-field">
      <span>{question.label}</span>
      <div className="setup-choice-list">
        {[
          { label: "Yes", value: true },
          { label: "No", value: false },
        ].map((option) => {
          const checked = draft.boolean_value === option.value;
          return (
            <label key={option.label} className={checked ? "setup-choice is-selected" : "setup-choice"}>
              <input
                type="radio"
                name={`setup-boolean-${question.question_id}`}
                checked={checked}
                disabled={disabled}
                onChange={() => {
                  on_change({
                    ...draft,
                    boolean_value: option.value,
                  });
                }}
              />
              <span className="setup-choice-copy">
                <strong>{option.label}</strong>
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

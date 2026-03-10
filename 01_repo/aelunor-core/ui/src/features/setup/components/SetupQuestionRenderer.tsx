import type { SetupQuestionPayload } from "../../../shared/api/contracts";
import type { SetupDraftState } from "../questionRegistry";
import { setupQuestionRegistry } from "../questionRegistry";

interface SetupQuestionRendererProps {
  question: SetupQuestionPayload;
  draft: SetupDraftState;
  disabled: boolean;
  on_change: (draft: SetupDraftState) => void;
}

export function SetupQuestionRenderer({ question, draft, disabled, on_change }: SetupQuestionRendererProps) {
  const QuestionComponent = setupQuestionRegistry[question.type];

  if (!QuestionComponent) {
    return <div className="session-feedback error">This setup question type is not supported in v1 yet.</div>;
  }

  return <QuestionComponent question={question} draft={draft} disabled={disabled} on_change={on_change} />;
}

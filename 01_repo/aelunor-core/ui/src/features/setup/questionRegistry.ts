import type { ComponentType } from "react";

import type { SetupAnswerPayload, SetupQuestionPayload, SetupQuestionType } from "../../shared/api/contracts";
import { SetupBooleanQuestion } from "./components/SetupBooleanQuestion";
import { SetupMultiSelectQuestion } from "./components/SetupMultiSelectQuestion";
import { SetupSelectQuestion } from "./components/SetupSelectQuestion";
import { SetupTextQuestion } from "./components/SetupTextQuestion";
import { SetupTextareaQuestion } from "./components/SetupTextareaQuestion";

export interface SetupDraftState {
  value: string;
  boolean_value: boolean | null;
  selected_value: string;
  selected_values: string[];
  other_text: string;
  other_values_text: string;
}

export interface SetupQuestionFieldProps {
  question: SetupQuestionPayload;
  draft: SetupDraftState;
  disabled: boolean;
  on_change: (draft: SetupDraftState) => void;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function readBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function readStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string" && entry.length > 0) : [];
}

export function createInitialSetupDraft(question: SetupQuestionPayload): SetupDraftState {
  const existing = question.existing_answer;
  const record = readRecord(existing);

  if (question.type === "text" || question.type === "textarea") {
    return {
      value: readString(existing),
      boolean_value: null,
      selected_value: "",
      selected_values: [],
      other_text: "",
      other_values_text: "",
    };
  }

  if (question.type === "boolean") {
    const boolValue = readBoolean(existing);
    return {
      value: "",
      boolean_value:
        boolValue ?? (readString(existing).toLowerCase() === "ja" ? true : readString(existing).toLowerCase() === "nein" ? false : null),
      selected_value: "",
      selected_values: [],
      other_text: "",
      other_values_text: "",
    };
  }

  if (question.type === "select") {
    const selected = readString(record.selected);
    return {
      value: "",
      boolean_value: null,
      selected_value: selected === "Sonstiges" ? "__other__" : selected,
      selected_values: [],
      other_text: readString(record.other_text),
      other_values_text: "",
    };
  }

  return {
    value: "",
    boolean_value: null,
    selected_value: "",
    selected_values: readStringArray(record.selected),
    other_text: "",
    other_values_text: readStringArray(record.other_values).join(", "),
  };
}

function parseOtherValues(value: string): string[] {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function buildSetupAnswerPayload(question: SetupQuestionPayload, draft: SetupDraftState): SetupAnswerPayload {
  if (question.type === "text" || question.type === "textarea") {
    return {
      question_id: question.question_id,
      value: draft.value.trim(),
    };
  }

  if (question.type === "boolean") {
    return {
      question_id: question.question_id,
      value: draft.boolean_value,
    };
  }

  if (question.type === "select") {
    return {
      question_id: question.question_id,
      value: draft.selected_value === "__other__" ? "" : draft.selected_value,
      other_text: draft.selected_value === "__other__" ? draft.other_text.trim() : "",
    };
  }

  return {
    question_id: question.question_id,
    selected: draft.selected_values,
    other_values: question.allow_other ? parseOtherValues(draft.other_values_text) : [],
  };
}

export function draftHasAnswer(question: SetupQuestionPayload, draft: SetupDraftState): boolean {
  if (question.type === "text" || question.type === "textarea") {
    return draft.value.trim().length > 0;
  }
  if (question.type === "boolean") {
    return draft.boolean_value !== null;
  }
  if (question.type === "select") {
    if (draft.selected_value === "__other__") {
      return draft.other_text.trim().length > 0;
    }
    return draft.selected_value.trim().length > 0;
  }
  return draft.selected_values.length > 0 || parseOtherValues(draft.other_values_text).length > 0;
}

export const setupQuestionRegistry: Record<SetupQuestionType, ComponentType<SetupQuestionFieldProps>> = {
  text: SetupTextQuestion,
  textarea: SetupTextareaQuestion,
  boolean: SetupBooleanQuestion,
  select: SetupSelectQuestion,
  multiselect: SetupMultiSelectQuestion,
};

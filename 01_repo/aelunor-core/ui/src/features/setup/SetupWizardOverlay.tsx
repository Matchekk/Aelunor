import { useEffect, useMemo, useRef, useState } from "react";

import type {
  CampaignSnapshot,
  SetupAnswerPayload,
  SetupPromptState,
  SetupQuestionPayload,
  SetupRandomResponse,
} from "../../shared/api/contracts";
import { deriveSetupPresenceKind, usePresenceActivityHeartbeat } from "../../entities/presence/activity";
import { usePresenceStore } from "../../entities/presence/store";
import { useSurfaceLayer } from "../../shared/ui/useSurfaceLayer";
import { useWaitingSignal } from "../../shared/waiting/hooks";
import { WaitingInline, WaitingSectionOverlay, WaitingSurface } from "../../shared/waiting/components";
import { useSetupAnswerMutation, useSetupNextMutation, useSetupRandomApplyMutation, useSetupRandomMutation } from "./mutations";
import {
  buildSetupAnswerPayload,
  createInitialSetupDraft,
  draftHasAnswer,
  type SetupDraftState,
} from "./questionRegistry";
import {
  canSkipQuestion,
  deriveSetupGateState,
  deriveSetupProgressSummary,
  deriveSetupReviewEntries,
  deriveSetupWaitingMessage,
} from "./selectors";
import { RandomSuggestionPanel } from "./components/RandomSuggestionPanel";
import { ReviewPanel } from "./components/ReviewPanel";
import { SetupActionBar } from "./components/SetupActionBar";
import { SetupHeader } from "./components/SetupHeader";
import { SetupProgress } from "./components/SetupProgress";
import { SetupQuestionRenderer } from "./components/SetupQuestionRenderer";

interface SetupWizardOverlayProps {
  campaign: CampaignSnapshot;
}

function asErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unexpected setup error.";
}

function samePrompt(left: SetupPromptState | null, right: SetupPromptState | null): boolean {
  if (!left || !right) {
    return false;
  }
  return (
    left.question.question_id === right.question.question_id &&
    left.progress.step === right.progress.step &&
    left.progress.total === right.progress.total
  );
}

function pushPrompt(stack: SetupPromptState[], index: number, prompt: SetupPromptState) {
  const current = stack[index] ?? null;
  if (samePrompt(current, prompt)) {
    if (current === prompt) {
      return {
        stack,
        index,
      };
    }

    const next = [...stack];
    next[index] = prompt;
    return {
      stack: next,
      index,
    };
  }

  const next = stack.slice(0, Math.max(index + 1, 0));
  next.push(prompt);
  return {
    stack: next,
    index: next.length - 1,
  };
}

function buildTurboFallbackAnswer(question: SetupQuestionPayload): SetupAnswerPayload {
  const timestamp = new Date().toISOString().slice(11, 19).replace(/:/g, "");
  if (question.type === "text" || question.type === "textarea") {
    return {
      question_id: question.question_id,
      value: `Auto-${timestamp} ${question.label || "Antwort"}`,
    };
  }

  if (question.type === "boolean") {
    return {
      question_id: question.question_id,
      value: Math.random() > 0.35,
    };
  }

  if (question.type === "select") {
    const optionValues =
      question.option_entries && question.option_entries.length > 0
        ? question.option_entries.map((entry) => entry.value).filter((value) => value.length > 0)
        : question.options ?? [];
    const selected = optionValues.length > 0 ? optionValues[Math.floor(Math.random() * optionValues.length)] ?? "" : "";
    const canUseOther = Boolean(question.allow_other);
    return {
      question_id: question.question_id,
      value: selected,
      other_text: selected ? "" : canUseOther ? "Auto-Auswahl" : "",
    };
  }

  const multiValues =
    question.option_entries && question.option_entries.length > 0
      ? question.option_entries.map((entry) => entry.value).filter((value) => value.length > 0)
      : question.options ?? [];
  const shuffled = [...multiValues].sort(() => Math.random() - 0.5);
  const minSelected = Number.isFinite(question.min_selected as number) ? Math.max(0, Number(question.min_selected)) : 1;
  const maxSelected = Number.isFinite(question.max_selected as number)
    ? Math.max(1, Number(question.max_selected))
    : Math.max(1, shuffled.length);
  const preferredCount = Math.max(minSelected, 1);
  const boundedCount = Math.max(1, Math.min(preferredCount, maxSelected, shuffled.length));
  const selected = shuffled.slice(0, boundedCount);
  const canUseOther = Boolean(question.allow_other);

  return {
    question_id: question.question_id,
    selected,
    other_values: selected.length > 0 ? [] : canUseOther ? ["Auto-Auswahl"] : [],
  };
}

export function SetupWizardOverlay({ campaign }: SetupWizardOverlayProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const gate = useMemo(() => deriveSetupGateState(campaign), [campaign]);
  const blockingAction = usePresenceStore((state) => state.blockingAction);
  const [promptStack, setPromptStack] = useState<SetupPromptState[]>([]);
  const [promptIndex, setPromptIndex] = useState(-1);
  const [draft, setDraft] = useState<SetupDraftState | null>(null);
  const [reviewActive, setReviewActive] = useState(false);
  const [reviewPayload, setReviewPayload] = useState<SetupAnswerPayload | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [randomOpen, setRandomOpen] = useState(false);
  const [randomMode, setRandomMode] = useState<"single" | "all">("single");
  const [randomPreview, setRandomPreview] = useState<SetupRandomResponse | null>(null);
  const [turboPending, setTurboPending] = useState(false);

  const flowKey = `${campaign.campaign_meta.campaign_id}:${gate.mode ?? "none"}:${gate.slot_id ?? ""}`;

  useEffect(() => {
    setPromptStack([]);
    setPromptIndex(-1);
    setDraft(null);
    setReviewActive(false);
    setReviewPayload(null);
    setLocalError(null);
    setRandomOpen(false);
    setRandomMode("single");
    setRandomPreview(null);
    setTurboPending(false);
  }, [flowKey]);

  useEffect(() => {
    if (!gate.current_prompt) {
      return;
    }

    const next = pushPrompt(promptStack, promptIndex, gate.current_prompt);
    if (next.stack !== promptStack || next.index !== promptIndex) {
      setPromptStack(next.stack);
      setPromptIndex(next.index);
    }
  }, [gate.current_prompt, promptIndex, promptStack]);

  const currentPrompt = promptStack[promptIndex] ?? gate.current_prompt;

  useEffect(() => {
    if (!currentPrompt?.question) {
      setDraft(null);
      return;
    }
    setDraft(createInitialSetupDraft(currentPrompt.question));
    setLocalError(null);
    setReviewActive(false);
    setReviewPayload(null);
    setRandomOpen(false);
    setRandomPreview(null);
  }, [currentPrompt?.question.question_id]);

  const scope =
    gate.mode !== null
      ? {
          campaign_id: campaign.campaign_meta.campaign_id,
          mode: gate.mode,
          slot_id: gate.slot_id,
        }
      : {
          campaign_id: campaign.campaign_meta.campaign_id,
          mode: "world" as const,
          slot_id: null,
        };

  const nextMutation = useSetupNextMutation(scope);
  const answerMutation = useSetupAnswerMutation(scope);
  const randomMutation = useSetupRandomMutation(scope);
  const randomApplyMutation = useSetupRandomApplyMutation(scope);

  const submitPending = nextMutation.isPending || answerMutation.isPending;
  const randomPending = randomMutation.isPending;
  const applyPending = randomApplyMutation.isPending;
  const sharedBlocked = Boolean(blockingAction);
  const disabledByBlocking = sharedBlocked && !submitPending && !randomPending && !applyPending && !turboPending;

  useWaitingSignal({
    key: `setup-host-wait:${campaign.campaign_meta.campaign_id}`,
    active: gate.requires_overlay && gate.is_waiting,
    context: "setup_waiting_host",
    scope: "section",
    blocking_level: "major_blocking",
    surface_target: "setup_overlay",
    detail_override: deriveSetupWaitingMessage(campaign),
  });

  useWaitingSignal({
    key: `setup-question-pending:${campaign.campaign_meta.campaign_id}`,
    active: gate.requires_overlay && submitPending && !gate.is_waiting,
    context: "setup_step",
    scope: "surface",
    blocking_level: "local_blocking",
    surface_target: "setup_question",
  });

  useWaitingSignal({
    key: `setup-side-pending:${campaign.campaign_meta.campaign_id}`,
    active: gate.requires_overlay && (randomPending || applyPending || turboPending) && !gate.is_waiting,
    context: randomPending || applyPending ? "setup_random" : "setup_step",
    scope: "surface",
    blocking_level: "local_blocking",
    surface_target: "setup_side",
  });

  useSurfaceLayer({
    open: gate.requires_overlay,
    kind: "modal",
    priority: 60,
    container: dialogRef.current,
    close_on_escape: false,
    trap_focus: true,
  });

  if (!gate.requires_overlay || !gate.mode) {
    return null;
  }

  const mutationError = answerMutation.isError
    ? asErrorMessage(answerMutation.error)
    : nextMutation.isError
      ? asErrorMessage(nextMutation.error)
      : randomMutation.isError
        ? asErrorMessage(randomMutation.error)
        : randomApplyMutation.isError
          ? asErrorMessage(randomApplyMutation.error)
          : null;

  const waitingMessage = deriveSetupWaitingMessage(campaign);
  const canInteractWithPrompt = gate.can_interact && Boolean(currentPrompt?.question) && Boolean(draft);
  const canSkip = canSkipQuestion(currentPrompt?.question ?? null);
  const canGoPrev = reviewActive || promptIndex > 0;
  const reviewEntries = deriveSetupReviewEntries(gate.summary_preview);
  const disabledReason = gate.is_waiting
    ? waitingMessage
    : gate.current_question
      ? deriveSetupProgressSummary(currentPrompt?.progress ?? gate.progress)
      : "Load the current setup step to continue.";

  usePresenceActivityHeartbeat({
    active: gate.requires_overlay && gate.can_interact && !gate.is_waiting && !submitPending && !randomPending && !applyPending,
    campaign_id: campaign.campaign_meta.campaign_id,
    kind: deriveSetupPresenceKind(gate.mode ?? "world"),
    slot_id: gate.mode === "character" ? gate.slot_id : null,
  });

  const submitAnswer = async (skip = false) => {
    if (!currentPrompt?.question) {
      return;
    }
    if (!draft && !reviewPayload) {
      return;
    }

    const payload =
      reviewActive && reviewPayload
        ? reviewPayload
        : skip
          ? { question_id: currentPrompt.question.question_id, value: "" }
          : buildSetupAnswerPayload(currentPrompt.question, draft as SetupDraftState);

    if (!skip && !reviewActive && currentPrompt.question.required && !draftHasAnswer(currentPrompt.question, draft as SetupDraftState)) {
      setLocalError("Answer this question before continuing.");
      return;
    }

    const isFinalQuestion = currentPrompt.progress.total > 0 && currentPrompt.progress.step >= currentPrompt.progress.total;
    if (!skip && !reviewActive && isFinalQuestion) {
      setReviewActive(true);
      setReviewPayload(payload);
      setLocalError(null);
      return;
    }

    setLocalError(null);
    setRandomOpen(false);
    await answerMutation.mutateAsync(payload);
    setReviewActive(false);
    setReviewPayload(null);
  };

  const loadCurrentStep = async () => {
    setLocalError(null);
    await nextMutation.mutateAsync();
  };

  const refreshRandomPreview = async (mode: "single" | "all" = randomMode) => {
    if (!currentPrompt?.question) {
      return;
    }
    const response = await randomMutation.mutateAsync({
      mode,
      question_id: currentPrompt.question.question_id,
      preview_answers: [],
    });
    setRandomPreview(response);
    setRandomOpen(true);
  };

  const applyRandomPreview = async () => {
    if (!randomPreview) {
      return;
    }
    await randomApplyMutation.mutateAsync({
      mode: randomPreview.mode,
      question_id: randomPreview.question_id ?? null,
      preview_answers: randomPreview.preview_answers.map((entry) => entry.answer),
    });
    setRandomOpen(false);
    setRandomPreview(null);
  };

  const runTurboRandom = async () => {
    if (!gate.can_interact || sharedBlocked || turboPending || submitPending || randomPending || applyPending) {
      return;
    }

    setLocalError(null);
    setRandomOpen(false);
    setRandomPreview(null);
    setTurboPending(true);

    try {
      let pendingQuestion: SetupQuestionPayload | null = currentPrompt?.question ?? null;
      let attempts = 0;
      while (attempts < 32) {
        if (!pendingQuestion) {
          const next = await nextMutation.mutateAsync();
          if (next.completed) {
            break;
          }
          pendingQuestion = next.question ?? null;
          if (!pendingQuestion) {
            break;
          }
        }

        attempts += 1;
        const fallbackPayload = buildTurboFallbackAnswer(pendingQuestion);
        const answered = await answerMutation.mutateAsync(fallbackPayload);
        if (answered.completed) {
          break;
        }
        pendingQuestion = answered.question ?? null;
      }
    } catch (error) {
      setLocalError(asErrorMessage(error));
    } finally {
      setTurboPending(false);
    }
  };

  return (
    <div className="setup-overlay-backdrop" role="presentation">
      <section ref={dialogRef} className="setup-overlay" role="dialog" aria-modal="true" aria-label="Setup wizard">
        <WaitingSectionOverlay target="setup_overlay" className="setup-waiting-overlay" />
        <SetupHeader
          title={gate.title}
          subtitle={gate.subtitle}
          phase_display={gate.phase_display}
          campaign_title={campaign.campaign_meta.title || "Campaign"}
        />

        <div className="setup-overlay-grid">
          <section className="setup-main-column">
            <SetupProgress
              chapter_label={gate.chapter_label}
              chapter_index={gate.chapter_index}
              chapter_total={gate.chapter_total}
              chapter_progress={gate.chapter_progress}
              global_progress={gate.global_progress}
              ready_counter={gate.ready_counter}
            />

            <section className="v1-panel setup-question-panel">
              <WaitingSurface target="setup_question" />
              <div className="v1-panel-head">
                <h2>{reviewActive ? "Review" : "Current Step"}</h2>
                <span>{gate.phase_display}</span>
              </div>
              <WaitingInline target="setup_question" className="hub-waiting-inline" />

              {mutationError ? <div className="session-feedback error">{mutationError}</div> : null}
              {localError ? <div className="session-feedback error">{localError}</div> : null}

              {gate.is_waiting ? (
                <div className="setup-empty-state">
                  <p>{waitingMessage}</p>
                  <p className="status-muted">
                    The host must finish the shared world questions before slot claims and character setup can continue.
                  </p>
                </div>
              ) : !currentPrompt?.question ? (
                <div className="setup-empty-state">
                  <p>No setup question is currently loaded for this step.</p>
                  <div className="setup-inline-actions">
                    <button type="button" onClick={() => void loadCurrentStep()} disabled={submitPending || sharedBlocked}>
                      {nextMutation.isPending ? "Loading..." : "Load current setup question"}
                    </button>
                  </div>
                </div>
              ) : reviewActive ? (
                <ReviewPanel mode={gate.mode} entries={reviewEntries} />
              ) : (
                <div className="setup-question-body">
                  <div className="setup-question-copy">
                    <p className="setup-ai-copy">{currentPrompt.question.ai_copy || currentPrompt.question.label}</p>
                    <p className="status-muted">
                      {currentPrompt.question.required ? "Required" : "Optional"} • {deriveSetupProgressSummary(currentPrompt.progress)}
                    </p>
                  </div>
                  {draft ? (
                    <SetupQuestionRenderer
                      question={currentPrompt.question}
                      draft={draft}
                      disabled={submitPending || randomPending || applyPending || sharedBlocked}
                      on_change={setDraft}
                    />
                  ) : null}
                </div>
              )}
            </section>
          </section>

          <aside className="setup-side-column">
            <WaitingSurface target="setup_side" />
            <WaitingInline target="setup_side" className="hub-waiting-inline" />
            <RandomSuggestionPanel
              open={randomOpen}
              preview={randomPreview}
              mode={randomMode}
              loading={randomPending}
              apply_pending={applyPending}
              disabled={sharedBlocked}
              on_mode_change={(mode) => {
                setRandomMode(mode);
                void refreshRandomPreview(mode);
              }}
              on_refresh={() => {
                void refreshRandomPreview(randomMode);
              }}
              on_apply={() => {
                void applyRandomPreview();
              }}
              on_close={() => {
                if (!randomPending && !applyPending) {
                  setRandomOpen(false);
                }
              }}
            />
            {!randomOpen ? (
              <section className="v1-panel setup-side-note">
                <div className="v1-panel-head">
                  <h2>Summary</h2>
                </div>
                <p className="status-muted">
                  {gate.is_waiting
                    ? waitingMessage
                    : reviewEntries.length > 0
                      ? `${reviewEntries.length} summary item${reviewEntries.length === 1 ? "" : "s"} available for review.`
                      : "The backend has not exposed a review summary for this step yet."}
                </p>
                {reviewEntries.length > 0 ? (
                  <div className="setup-review-grid compact">
                    {reviewEntries.slice(0, 4).map((entry) => (
                      <article key={entry.label} className="setup-review-item">
                        <strong>{entry.label}</strong>
                        <p>{entry.value}</p>
                      </article>
                    ))}
                  </div>
                ) : null}
              </section>
            ) : null}
          </aside>
        </div>

        {!gate.is_waiting && gate.can_interact ? (
          <SetupActionBar
            can_go_prev={canGoPrev}
            can_skip={canSkip && !reviewActive}
            can_randomize={gate.is_random_available && !reviewActive}
            can_turbo={!reviewActive}
            can_submit={Boolean((reviewActive && reviewPayload) || currentPrompt?.question)}
            disabled={sharedBlocked}
            submit_pending={submitPending}
            random_pending={randomPending}
            apply_pending={applyPending}
            turbo_pending={turboPending}
            blocking_hint={disabledByBlocking ? blockingAction?.label ?? "A shared action is still running." : null}
            disabled_reason={!canInteractWithPrompt ? disabledReason : null}
            submit_label={reviewActive ? "Confirm and save" : "Submit answer"}
            on_prev={() => {
              setLocalError(null);
              setRandomOpen(false);
              if (reviewActive) {
                setReviewActive(false);
                return;
              }
              setPromptIndex((current) => Math.max(0, current - 1));
            }}
            on_skip={() => {
              void submitAnswer(true);
            }}
            on_randomize={() => {
              setRandomOpen(true);
              void refreshRandomPreview(randomMode);
            }}
            on_turbo={() => {
              void runTurboRandom();
            }}
            on_submit={() => {
              void submitAnswer(false);
            }}
          />
        ) : null}
      </section>
    </div>
  );
}

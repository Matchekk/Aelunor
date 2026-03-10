import { useState } from "react";

import type { CampaignSnapshot, ContextQueryResponse } from "../../../shared/api/contracts";
import { usePresenceStore } from "../../../entities/presence/store";
import { getPlayModeConfig, type PlayModeId, PLAY_MODE_CONFIG } from "../modeConfig";
import { useContextQueryMutation, useSubmitTurnMutation } from "../mutations";
import {
  deriveComposerAccessState,
  deriveIntroBannerMessage,
  deriveLatestRequests,
} from "../selectors";
import { ComposerModeTabs } from "./ComposerModeTabs";
import { ComposerStatusBar } from "./ComposerStatusBar";
import { IntroBanner } from "./IntroBanner";
import { RequestsBlock } from "./RequestsBlock";
import { SubmitBar } from "./SubmitBar";

interface ComposerProps {
  campaign: CampaignSnapshot;
  on_open_context: (payload: ContextQueryResponse, return_focus: HTMLElement | null) => void;
}

function asErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unexpected error";
}

function initialDrafts(): Record<PlayModeId, string> {
  return PLAY_MODE_CONFIG.reduce<Record<PlayModeId, string>>((acc, mode) => {
    acc[mode.id] = "";
    return acc;
  }, {} as Record<PlayModeId, string>);
}

function activeElement(): HTMLElement | null {
  return document.activeElement instanceof HTMLElement ? document.activeElement : null;
}

export function Composer({ campaign, on_open_context }: ComposerProps) {
  const [currentMode, setCurrentMode] = useState<PlayModeId>("do");
  const [drafts, setDrafts] = useState<Record<PlayModeId, string>>(() => initialDrafts());

  const blockingAction = usePresenceStore((state) => state.blockingAction);
  const submitTurnMutation = useSubmitTurnMutation(campaign.campaign_meta.campaign_id);
  const contextQueryMutation = useContextQueryMutation(campaign.campaign_meta.campaign_id);

  const currentDraft = drafts[currentMode];
  const submitPending = submitTurnMutation.isPending || contextQueryMutation.isPending;
  const access = deriveComposerAccessState(campaign, currentMode, blockingAction, submitPending, currentDraft);
  const introMessage = deriveIntroBannerMessage(campaign);
  const latestRequests = deriveLatestRequests(campaign, access.actor);
  const modeConfig = getPlayModeConfig(currentMode);

  const mutationError = submitTurnMutation.isError
    ? asErrorMessage(submitTurnMutation.error)
    : contextQueryMutation.isError
      ? asErrorMessage(contextQueryMutation.error)
      : null;

  const setDraft = (value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [currentMode]: value,
    }));
  };

  const submit = async () => {
    if (!access.can_submit || !access.actor) {
      return;
    }

    const text = currentDraft.trim();
    if (!text) {
      return;
    }

    const returnFocus = activeElement();

    if (modeConfig.is_contextual) {
      const response = await contextQueryMutation.mutateAsync({
        actor: access.actor,
        text,
      });
      setDraft("");
      on_open_context(response, returnFocus);
      return;
    }

    await submitTurnMutation.mutateAsync({
      actor: access.actor,
      mode: modeConfig.backend_mode ?? modeConfig.label,
      text,
    });
    setDraft("");
  };

  return (
    <section className="v1-panel composer-panel">
      <div className="v1-panel-head">
        <h2>Composer</h2>
        <span>{modeConfig.label}</span>
      </div>

      <IntroBanner message={introMessage} />
      <RequestsBlock requests={latestRequests} />

      <ComposerModeTabs
        current_mode={currentMode}
        disabled={submitPending}
        on_change={(mode) => {
          setCurrentMode(mode);
        }}
      />

      <ComposerStatusBar
        actor={access.actor}
        mode_label={modeConfig.label}
        helper_text={access.helper_text}
        disabled_reason={access.disabled_reason}
      />

      <label className="composer-textarea-wrap">
        <span className="status-muted">Draft</span>
        <textarea
          value={currentDraft}
          onChange={(event) => {
            setDraft(event.target.value);
          }}
          placeholder={modeConfig.placeholder}
          rows={6}
          disabled={submitPending}
          onKeyDown={(event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
              event.preventDefault();
              void submit();
            }
          }}
        />
      </label>

      <SubmitBar
        submit_label={access.submit_label}
        pending={submitPending}
        disabled={!access.can_submit}
        error_message={mutationError}
        on_submit={() => {
          void submit();
        }}
      />
    </section>
  );
}

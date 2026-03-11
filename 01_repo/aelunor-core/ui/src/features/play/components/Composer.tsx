import { useEffect, useRef, useState } from "react";

import { derivePresenceKindForContext, usePresenceActivityClient } from "../../../entities/presence/activity";
import type { CampaignSnapshot, ContextQueryResponse } from "../../../shared/api/contracts";
import { usePresenceStore } from "../../../entities/presence/store";
import { resolveInitialComposerMode } from "../../../entities/settings/interaction";
import { useUserSettingsStore } from "../../../entities/settings/store";
import { deriveUserFacingErrorMessage } from "../../../shared/errors/userFacing";
import { getPlayModeConfig, type PlayModeId, PLAY_MODE_CONFIG } from "../modeConfig";
import { useContextQueryMutation, useSubmitTurnMutation } from "../mutations";
import { useWaitingSignal } from "../../../shared/waiting/hooks";
import { WaitingInline, WaitingSurface } from "../../../shared/waiting/components";
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
  return deriveUserFacingErrorMessage(error, "Die Aktion konnte gerade nicht abgeschlossen werden.");
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
  const composerModePreference = useUserSettingsStore((state) => state.interaction.composer_mode_preference);
  const setComposerModePreference = useUserSettingsStore((state) => state.set_composer_mode_preference);
  const [currentMode, setCurrentMode] = useState<PlayModeId>(() => resolveInitialComposerMode(composerModePreference));
  const [drafts, setDrafts] = useState<Record<PlayModeId, string>>(() => initialDrafts());
  const typingTimerRef = useRef<number | null>(null);

  const blockingAction = usePresenceStore((state) => state.blockingAction);
  const presenceActivity = usePresenceActivityClient(campaign.campaign_meta.campaign_id);
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

  useEffect(() => {
    setCurrentMode(resolveInitialComposerMode(composerModePreference));
  }, [composerModePreference]);

  useEffect(() => {
    return () => {
      if (typingTimerRef.current) {
        window.clearTimeout(typingTimerRef.current);
      }
      void presenceActivity.clear_activity();
    };
  }, [presenceActivity]);

  useWaitingSignal({
    key: `composer-turn-timeline:${campaign.campaign_meta.campaign_id}`,
    active: submitTurnMutation.isPending,
    context: "story_turn",
    scope: "inline",
    blocking_level: "non_blocking",
    surface_target: "timeline",
  });

  useWaitingSignal({
    key: `composer-turn-surface:${campaign.campaign_meta.campaign_id}`,
    active: submitTurnMutation.isPending,
    context: "story_turn",
    scope: "surface",
    blocking_level: "local_blocking",
    surface_target: "composer",
  });

  useWaitingSignal({
    key: `composer-context:${campaign.campaign_meta.campaign_id}`,
    active: contextQueryMutation.isPending,
    context: "context_query",
    scope: "inline",
    blocking_level: "local_blocking",
    surface_target: "composer",
  });

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
      void presenceActivity.clear_activity();
      on_open_context(response, returnFocus);
      return;
    }

    await submitTurnMutation.mutateAsync({
      actor: access.actor,
      mode: modeConfig.backend_mode ?? modeConfig.label,
      text,
    });
    setDraft("");
    void presenceActivity.clear_activity();
  };

  return (
    <section className="composer-dock hud-surface panel composer-panel">
      <WaitingSurface target="composer" />
      <div className="v1-panel-head composer-dock-head">
        <h2 className="panelTitle">Dein Beitrag</h2>
        <span>{modeConfig.label}</span>
      </div>

      {introMessage ? <IntroBanner message={introMessage} /> : null}
      {latestRequests.length > 0 ? <RequestsBlock requests={latestRequests} /> : null}

      <ComposerModeTabs
        current_mode={currentMode}
        disabled={submitPending}
        on_change={(mode) => {
          setCurrentMode(mode);
          if (mode === "do" || mode === "say" || mode === "story") {
            setComposerModePreference(mode);
          }
        }}
      />

      <ComposerStatusBar
        actor={access.actor}
        mode_label={modeConfig.label}
        helper_text={modeConfig.hint}
        disabled_reason={access.disabled_reason}
      />
      <WaitingInline target="composer" className="composer-waiting-inline" />

      <label className="composer-textarea-wrap">
        <span className="status-muted">Entwurf</span>
        <textarea
          value={currentDraft}
          onChange={(event) => {
            const nextValue = event.target.value;
            setDraft(nextValue);

            if (!access.actor || modeConfig.is_contextual) {
              return;
            }

            if (typingTimerRef.current) {
              window.clearTimeout(typingTimerRef.current);
              typingTimerRef.current = null;
            }

            if (!nextValue.trim()) {
              void presenceActivity.clear_activity();
              return;
            }

            typingTimerRef.current = window.setTimeout(() => {
              void presenceActivity.set_activity({
                kind: derivePresenceKindForContext("typing"),
                slot_id: access.actor,
              });
            }, 700);
          }}
          placeholder={modeConfig.placeholder}
          rows={4}
          disabled={submitPending}
          onBlur={() => {
            if (typingTimerRef.current) {
              window.clearTimeout(typingTimerRef.current);
              typingTimerRef.current = null;
            }
            void presenceActivity.clear_activity();
          }}
          onKeyDown={(event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
              event.preventDefault();
              void submit();
            }
          }}
        />
      </label>
      <p className="status-muted composer-helper">{access.helper_text}</p>

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

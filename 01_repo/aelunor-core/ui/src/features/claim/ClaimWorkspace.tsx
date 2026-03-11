import { useEffect, useMemo, useState } from "react";

import type { CampaignSnapshot } from "../../shared/api/contracts";
import { derivePresenceKindForContext, usePresenceActivityClient } from "../../entities/presence/activity";
import { usePresenceStore } from "../../entities/presence/store";
import { ClaimHeader } from "./components/ClaimHeader";
import { ClaimStatusBar } from "./components/ClaimStatusBar";
import { SlotCard } from "./components/SlotCard";
import { TakeoverConfirmDialog } from "./components/TakeoverConfirmDialog";
import { useClaimSlotMutation, useTakeoverSlotMutation, useUnclaimSlotMutation } from "./mutations";
import {
  type ClaimSlotViewModel,
  deriveClaimGateState,
  deriveClaimMetaLine,
  deriveClaimSlots,
  deriveClaimStatusMessage,
  deriveReadyProgressSummary,
} from "./selectors";

function asErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unexpected error";
}

interface ClaimWorkspaceProps {
  campaign: CampaignSnapshot;
  join_code: string | null;
  on_leave_session: () => void;
}

function activeElement(): HTMLElement | null {
  return document.activeElement instanceof HTMLElement ? document.activeElement : null;
}

export function ClaimWorkspace({ campaign, join_code, on_leave_session }: ClaimWorkspaceProps) {
  const gate = useMemo(() => deriveClaimGateState(campaign), [campaign]);
  const slots = useMemo(() => deriveClaimSlots(campaign), [campaign]);
  const readySummary = useMemo(() => deriveReadyProgressSummary(campaign), [campaign]);
  const message = useMemo(() => deriveClaimStatusMessage(campaign), [campaign]);
  const blockingAction = usePresenceStore((state) => state.blockingAction);
  const presenceActivity = usePresenceActivityClient(campaign.campaign_meta.campaign_id);

  const claimMutation = useClaimSlotMutation(campaign.campaign_meta.campaign_id);
  const takeoverMutation = useTakeoverSlotMutation(campaign.campaign_meta.campaign_id);
  const unclaimMutation = useUnclaimSlotMutation(campaign.campaign_meta.campaign_id);

  const [takeoverTarget, setTakeoverTarget] = useState<ClaimSlotViewModel | null>(null);
  const [takeoverReturnFocus, setTakeoverReturnFocus] = useState<HTMLElement | null>(null);

  const anyMutationPending = claimMutation.isPending || takeoverMutation.isPending || unclaimMutation.isPending;
  const blockingHint = blockingAction?.label ?? null;
  const mutationError = claimMutation.isError
    ? asErrorMessage(claimMutation.error)
    : takeoverMutation.isError
      ? asErrorMessage(takeoverMutation.error)
      : unclaimMutation.isError
        ? asErrorMessage(unclaimMutation.error)
        : null;

  useEffect(() => {
    return () => {
      void presenceActivity.clear_activity();
    };
  }, [presenceActivity]);

  return (
    <main className="v1-app-shell session-hub-shell claim-workspace-shell">
      <ClaimHeader
        title={campaign.campaign_meta.title || "Campaign"}
        meta_line={deriveClaimMetaLine(campaign)}
        join_code={join_code}
        on_leave_session={on_leave_session}
      />

      <ClaimStatusBar
        gate={gate}
        ready_summary={readySummary}
        message={message}
        mutation_error={mutationError}
        blocking_hint={blockingHint}
        has_slots={slots.length > 0}
      />

      <section className="claim-slot-grid">
        {slots.length === 0 ? (
          <section className="v1-panel claim-empty-state">
            <div className="v1-panel-head">
              <h2>No Claimable Slots</h2>
            </div>
            <p className="status-muted">
              This campaign snapshot does not currently expose any slot entries. You can return to Session Hub or wait
              for the campaign configuration to change.
            </p>
          </section>
        ) : (
          slots.map((slot) => {
            const pendingAction =
              claimMutation.isPending && claimMutation.variables === slot.slot_id
                ? "claim"
                : takeoverMutation.isPending && takeoverMutation.variables === slot.slot_id
                  ? "takeover"
                  : unclaimMutation.isPending && unclaimMutation.variables === slot.slot_id
                    ? "unclaim"
                    : null;

            return (
              <SlotCard
                key={slot.slot_id}
                slot={slot}
                disabled={anyMutationPending || Boolean(blockingAction)}
                pending_action={pendingAction}
                on_claim={(slot_id) => {
                  void (async () => {
                    void presenceActivity.set_activity({
                      kind: derivePresenceKindForContext("slot_claim"),
                      slot_id,
                    });
                    try {
                      await claimMutation.mutateAsync(slot_id);
                    } finally {
                      void presenceActivity.clear_activity();
                    }
                  })();
                }}
                on_takeover={(nextSlot) => {
                  setTakeoverReturnFocus(activeElement());
                  setTakeoverTarget(nextSlot);
                }}
                on_unclaim={(slot_id) => {
                  void unclaimMutation.mutateAsync(slot_id);
                }}
              />
            );
          })
        )}
      </section>

      <TakeoverConfirmDialog
        open={Boolean(takeoverTarget)}
        slot={takeoverTarget}
        pending={takeoverMutation.isPending}
        error_message={takeoverMutation.isError ? asErrorMessage(takeoverMutation.error) : null}
        return_focus_element={takeoverReturnFocus}
        on_close={() => {
          if (!takeoverMutation.isPending) {
            setTakeoverTarget(null);
          }
        }}
        on_confirm={(slot_id) => {
          void (async () => {
            void presenceActivity.set_activity({
              kind: derivePresenceKindForContext("slot_claim"),
              slot_id,
            });
            try {
              await takeoverMutation.mutateAsync(slot_id, {
                onSuccess: () => {
                  setTakeoverTarget(null);
                },
              });
            } finally {
              void presenceActivity.clear_activity();
            }
          })();
        }}
      />
    </main>
  );
}

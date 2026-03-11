import { useMemo } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import { deriveUserFacingErrorMessage } from "../../../shared/errors/userFacing";
import { campaignHasIntro, deriveIntroState, derivePlayPhaseState } from "../selectors";

interface PrePlayOverviewProps {
  campaign: CampaignSnapshot;
  on_open_boards: () => void;
  on_retry_intro: () => void;
  intro_retry_pending: boolean;
}

function deriveReadyCounter(campaign: CampaignSnapshot): { ready: number; total: number } {
  const fromRuntime = campaign.setup_runtime.ready_counter;
  if (fromRuntime && Number.isFinite(fromRuntime.ready) && Number.isFinite(fromRuntime.total)) {
    return {
      ready: Math.max(0, fromRuntime.ready),
      total: Math.max(0, fromRuntime.total),
    };
  }

  const statuses = campaign.setup_runtime.slot_statuses ?? campaign.setup_runtime.world?.slot_statuses ?? [];
  return {
    ready: statuses.filter((status) => status.completed || status.status === "ready").length,
    total: statuses.length,
  };
}

export function PrePlayOverview({ campaign, on_open_boards, on_retry_intro, intro_retry_pending }: PrePlayOverviewProps) {
  const phaseState = derivePlayPhaseState(campaign);
  const readyCounter = useMemo(() => deriveReadyCounter(campaign), [campaign]);
  const introState = deriveIntroState(campaign);
  const hasIntro = campaignHasIntro(campaign);
  const host = campaign.players.find((player) => player.player_id === campaign.campaign_meta.host_player_id) ?? null;
  const claimedSlots = campaign.available_slots.filter((slot) => Boolean(slot.claimed_by)).length;
  const canStartSoon = readyCounter.total > 0 && readyCounter.ready >= readyCounter.total;
  const canRetryIntro = campaign.viewer_context.is_host && phaseState.is_ready_to_start && !hasIntro;

  let nextStepTitle = phaseState.is_ready_to_start ? "Auf Eröffnungszug warten" : "Auf aktive Phase warten";
  let nextStepDescription =
    "Währenddessen kannst du Boards prüfen und den bisherigen Verlauf lesen. Züge werden erst in der aktiven Phase freigeschaltet.";

  if (!hasIntro && introState.status === "failed") {
    nextStepTitle = "Eröffnungszug fehlgeschlagen";
    nextStepDescription = deriveUserFacingErrorMessage(
      introState.last_error ? new Error(introState.last_error) : null,
      "Der Eröffnungszug konnte nicht erzeugt werden. Bitte versuche es erneut.",
    );
  } else if (!hasIntro && introState.status === "pending") {
    nextStepTitle = "Eröffnungszug wird erstellt";
    nextStepDescription = "Die Kampagne baut gerade den ersten Storyzug auf. Die aktive Spielphase startet danach automatisch.";
  }

  return (
    <section className="v1-panel preplay-overview story-surface">
      <div className="v1-panel-head">
        <h2>Kampagnenstatus</h2>
        <span>{phaseState.phase_display}</span>
      </div>
      <div className="preplay-grid">
        <article className="preplay-card">
          <h3>Bereitschaft</h3>
          <p className="preplay-highlight">
            {readyCounter.total > 0 ? `Bereit ${readyCounter.ready}/${readyCounter.total}` : "Bereitschaft wird geladen"}
          </p>
          <p className="status-muted">
            {canStartSoon
              ? "Alle bekannten Slots sind vorbereitet. Der Übergang in die aktive Spielphase steht bevor."
              : "Die Kampagne ist vorbereitet, aber noch nicht in der aktiven Spielphase."}
          </p>
        </article>
        <article className="preplay-card">
          <h3>Gruppe</h3>
          <p className="preplay-highlight">{campaign.players.length} Spieler verbunden</p>
          <p className="status-muted">
            {claimedSlots} belegte Slots
            {host ? ` • Host: ${host.display_name}` : ""}
          </p>
        </article>
        <article className="preplay-card">
          <h3>Nächster Schritt</h3>
          <p className="preplay-highlight">{nextStepTitle}</p>
          <p className="status-muted">{nextStepDescription}</p>
          <div className="preplay-actions">
            {canRetryIntro ? (
              <button type="button" onClick={on_retry_intro} disabled={intro_retry_pending}>
                {intro_retry_pending ? "Eröffnungszug läuft..." : "Eröffnungszug starten"}
              </button>
            ) : null}
            <button type="button" onClick={on_open_boards}>
              Boards öffnen
            </button>
          </div>
        </article>
      </div>
    </section>
  );
}

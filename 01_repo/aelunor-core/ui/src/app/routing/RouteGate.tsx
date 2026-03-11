import type { ReactElement } from "react";

import { Navigate, useLocation } from "react-router-dom";

import type { SessionBootstrap } from "../bootstrap/sessionStorage";
import { HttpClientError } from "../../shared/api/httpClient";
import { deriveUserFacingErrorMessage } from "../../shared/errors/userFacing";
import { useCampaignQuery } from "../../entities/campaign/queries";
import { PresenceProvider } from "../providers/PresenceProvider";
import { ClaimWorkspace } from "../../features/claim/ClaimWorkspace";
import { CampaignWorkspace } from "../../features/play/CampaignWorkspace";
import { SessionHubWorkspace } from "../../features/session/SessionHubWorkspace";
import { hasActiveSession } from "../../features/session/selectors";
import { SetupWizardOverlay } from "../../features/setup/SetupWizardOverlay";
import { WaitingFullStage } from "../../shared/waiting/components";
import { buildCampaignPath, buildV1HubPath, buildV1RootPath, normalizePlayRouteState, parseV1RouteIntent, serializePlayRouteState } from "./routes";
import { deriveRootRedirectTarget, deriveRouteIntentResolution, deriveRouteRenderState } from "./selectors";

interface RouteGateProps {
  active_session: SessionBootstrap;
  on_active_session_change: (session: SessionBootstrap) => void;
  on_clear_active_session: () => void;
}

interface HubRouteState {
  hub_error_message?: string;
}

function isStaleSessionError(error: unknown): boolean {
  return error instanceof HttpClientError && [401, 403, 404].includes(error.status);
}

function asErrorMessage(error: unknown): string {
  return deriveUserFacingErrorMessage(error, "Der Kampagnenstatus konnte gerade nicht geladen werden.");
}

function renderCampaignLoadFailure(on_clear_active_session: () => void, on_retry: () => void, error: unknown): ReactElement {
  return (
    <main className="v1-app-shell session-hub-shell">
      <section className="v1-panel session-route-banner">
        <div className="v1-panel-head">
          <h2>Kampagne konnte nicht geladen werden</h2>
          <span>Wiederherstellung</span>
        </div>
        <div className="session-feedback error">{asErrorMessage(error)}</div>
        <p className="status-muted">
          Deine Sitzung ist vorhanden, aber der Kampagnen-Snapshot ist aktuell nicht verfügbar.
        </p>
        <div className="session-inline-actions">
          <button type="button" onClick={on_retry}>
            Erneut versuchen
          </button>
          <button type="button" onClick={on_clear_active_session}>
            Sitzung zurücksetzen
          </button>
        </div>
      </section>
    </main>
  );
}

export function RouteGate({
  active_session,
  on_active_session_change,
  on_clear_active_session,
}: RouteGateProps) {
  const location = useLocation();
  const intent = parseV1RouteIntent(location.pathname);
  const hubRouteState = (location.state ?? {}) as HubRouteState;
  const sessionIsActive = hasActiveSession(active_session);
  const shouldFetchCampaign = sessionIsActive && (intent.kind === "root" || intent.kind === "campaign");
  const campaignQuery = useCampaignQuery(shouldFetchCampaign ? active_session.campaign_id : null);
  const campaignLoading =
    shouldFetchCampaign && (campaignQuery.isPending || (intent.kind === "root" && !campaignQuery.data && !campaignQuery.isError));

  if (intent.kind === "unknown") {
    return <Navigate to={sessionIsActive ? buildV1RootPath() : buildV1HubPath()} replace />;
  }

  if (intent.kind === "hub") {
    return (
      <SessionHubWorkspace
        active_session={active_session}
        on_active_session_change={on_active_session_change}
        route_error_message={hubRouteState.hub_error_message ?? null}
      />
    );
  }

  if (!sessionIsActive) {
    return (
      <Navigate
        to={buildV1HubPath()}
        replace
        state={
          intent.kind === "campaign"
            ? {
                hub_error_message:
                  "Diese Kampagnen-URL braucht eine gültige lokale Sitzung. Bitte im Hub fortsetzen oder erneut beitreten.",
              }
            : undefined
        }
      />
    );
  }

  if (campaignLoading) {
    return (
      <WaitingFullStage
        target="route_gate"
        context="campaign_open"
        active={true}
        heading="Kampagne wird geöffnet"
        detail="Der aktuelle Snapshot wird vorbereitet."
      />
    );
  }

  if (campaignQuery.isError || !campaignQuery.data) {
    if (isStaleSessionError(campaignQuery.error)) {
      return (
        <Navigate
          to={buildV1HubPath()}
          replace
          state={{
            hub_error_message:
              "Die gespeicherten Zugangsdaten passen nicht mehr zu einer ladbaren Kampagne. Bitte im Hub die Sitzung neu verbinden.",
          }}
        />
      );
    }

    return renderCampaignLoadFailure(on_clear_active_session, () => void campaignQuery.refetch(), campaignQuery.error);
  }

  const campaign = campaignQuery.data;

  if (intent.kind === "root") {
    const rootTarget = deriveRootRedirectTarget(active_session, campaign);
    return <Navigate to={rootTarget === "hub" ? buildV1HubPath() : buildCampaignPath(campaign.campaign_meta.campaign_id, rootTarget)} replace />;
  }

  if (intent.campaign_id !== active_session.campaign_id) {
    return <Navigate to={buildCampaignPath(campaign.campaign_meta.campaign_id, deriveRouteRenderState(campaign).canonical_workspace)} replace />;
  }

  const routeResolution = deriveRouteIntentResolution(intent, campaign);
  if (routeResolution.should_redirect) {
    return <Navigate to={buildCampaignPath(campaign.campaign_meta.campaign_id, routeResolution.target_workspace)} replace />;
  }

  if (intent.workspace === "play") {
    const normalizedPlayState = normalizePlayRouteState(campaign, location.search);
    const normalizedSearch = serializePlayRouteState(normalizedPlayState);
    if (normalizedSearch !== location.search) {
      return <Navigate to={`${buildCampaignPath(campaign.campaign_meta.campaign_id, "play")}${normalizedSearch}`} replace />;
    }
  } else if ((intent.workspace === "claim" || intent.workspace === "setup") && location.search) {
    return <Navigate to={buildCampaignPath(campaign.campaign_meta.campaign_id, intent.workspace)} replace />;
  }

  const routeState = deriveRouteRenderState(campaign);

  return (
    <PresenceProvider session={active_session}>
      <>
        {routeState.workspace === "claim" ? (
          <ClaimWorkspace
            campaign={campaign}
            join_code={active_session.join_code}
            on_leave_session={on_clear_active_session}
          />
        ) : (
          <CampaignWorkspace
            campaign={campaign}
            session={active_session}
            on_clear_active_session={on_clear_active_session}
          />
        )}
        {routeState.show_setup_overlay ? <SetupWizardOverlay campaign={campaign} /> : null}
      </>
    </PresenceProvider>
  );
}

import type { ReactElement } from "react";

import { Navigate, useLocation } from "react-router-dom";

import type { SessionBootstrap } from "../bootstrap/sessionStorage";
import { HttpClientError } from "../../shared/api/httpClient";
import { useCampaignQuery } from "../../entities/campaign/queries";
import { PresenceProvider } from "../providers/PresenceProvider";
import { ClaimWorkspace } from "../../features/claim/ClaimWorkspace";
import { CampaignWorkspace } from "../../features/play/CampaignWorkspace";
import { SessionHubWorkspace } from "../../features/session/SessionHubWorkspace";
import { hasActiveSession } from "../../features/session/selectors";
import { SetupWizardOverlay } from "../../features/setup/SetupWizardOverlay";
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
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unable to load campaign state.";
}

function renderLoadingScreen(): ReactElement {
  return (
    <main className="v1-app-shell session-hub-shell">
      <section className="v1-panel session-route-banner">
        <div className="v1-panel-head">
          <h2>Loading Campaign</h2>
          <span>Snapshot bootstrap</span>
        </div>
        <p className="status-muted">Fetching the latest campaign snapshot for the requested v1 route.</p>
      </section>
    </main>
  );
}

function renderCampaignLoadFailure(on_clear_active_session: () => void, on_retry: () => void, error: unknown): ReactElement {
  return (
    <main className="v1-app-shell session-hub-shell">
      <section className="v1-panel session-route-banner">
        <div className="v1-panel-head">
          <h2>Campaign Load Failed</h2>
          <span>Route recovery</span>
        </div>
        <div className="session-feedback error">{asErrorMessage(error)}</div>
        <p className="status-muted">
          The current session exists, but the campaign snapshot could not be loaded for this route right now.
        </p>
        <div className="session-inline-actions">
          <button type="button" onClick={on_retry}>
            Retry fetch
          </button>
          <button type="button" onClick={on_clear_active_session}>
            Clear active session
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
                hub_error_message: "This campaign URL requires a valid local session. Resume or join the campaign from Session Hub.",
              }
            : undefined
        }
      />
    );
  }

  if (campaignQuery.isPending || (intent.kind === "root" && !campaignQuery.data && !campaignQuery.isError)) {
    return renderLoadingScreen();
  }

  if (campaignQuery.isError || !campaignQuery.data) {
    if (isStaleSessionError(campaignQuery.error)) {
      return (
        <Navigate
          to={buildV1HubPath()}
          replace
          state={{
            hub_error_message:
              "Stored credentials no longer match a loadable campaign session. Clear or recover the local session from the library.",
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

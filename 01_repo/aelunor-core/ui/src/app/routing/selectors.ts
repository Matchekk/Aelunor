import type { SessionBootstrap } from "../bootstrap/sessionStorage";
import type { CampaignSnapshot } from "../../shared/api/contracts";
import { deriveClaimGateState } from "../../features/claim/selectors";
import { deriveSetupGateState } from "../../features/setup/selectors";
import type { CampaignRouteWorkspace, ParsedV1RouteIntent } from "./routes";

export interface RouteRenderState {
  workspace: "claim" | "play";
  canonical_workspace: CampaignRouteWorkspace;
  show_setup_overlay: boolean;
}

export interface RouteIntentResolution {
  should_redirect: boolean;
  target_workspace: CampaignRouteWorkspace;
}

export function deriveRouteRenderState(campaign: CampaignSnapshot): RouteRenderState {
  const claimGate = deriveClaimGateState(campaign);
  const setupGate = deriveSetupGateState(campaign);
  const workspace = claimGate.requires_claim_workspace ? "claim" : "play";
  const canonical_workspace: CampaignRouteWorkspace = setupGate.requires_overlay ? "setup" : workspace;

  return {
    workspace,
    canonical_workspace,
    show_setup_overlay: setupGate.requires_overlay,
  };
}

export function deriveRouteIntentResolution(intent: ParsedV1RouteIntent, campaign: CampaignSnapshot): RouteIntentResolution {
  const renderState = deriveRouteRenderState(campaign);

  return {
    should_redirect: intent.kind !== "campaign" || intent.workspace !== renderState.canonical_workspace,
    target_workspace: renderState.canonical_workspace,
  };
}

export function deriveRootRedirectTarget(session: SessionBootstrap | null, campaign: CampaignSnapshot | null): CampaignRouteWorkspace | "hub" {
  if (!session?.campaign_id || !campaign) {
    return "hub";
  }

  return deriveRouteRenderState(campaign).canonical_workspace;
}


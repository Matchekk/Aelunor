import type { CampaignSnapshot, ContextQueryResponse, ContextQueryResultSource } from "../../shared/api/contracts";
import { partyScopeLabel, sceneScopeLabel, selfScopeLabel, type ScopeLabelDescriptor } from "../scenes/scopeLabels";

export function deriveContextTitle(payload: ContextQueryResponse): string {
  return payload.result.title || payload.result.target || "Context result";
}

export function deriveContextScopeLabels(payload: ContextQueryResponse, campaign: CampaignSnapshot): ScopeLabelDescriptor[] {
  const labels: ScopeLabelDescriptor[] = [];
  const entityType = payload.result.entity_type || "unknown";
  const entityId = payload.result.entity_id || "";
  const actor = payload.actor || campaign.viewer_context.claimed_slot_id || "";

  if (entityType === "scene") {
    labels.push(sceneScopeLabel(payload.result.title || entityId, entityId));
  } else if ((entityType === "class" || entityType === "skill") && actor && entityId.startsWith(`${actor}:`)) {
    labels.push(selfScopeLabel());
  } else if (entityType === "race" || entityType === "beast" || entityType === "npc" || entityType === "plotpoint" || entityType === "faction") {
    labels.push(partyScopeLabel());
  }

  return labels;
}

export function deriveContextSourceKinds(sources: ContextQueryResultSource[]): string[] {
  return Array.from(
    new Set(
      sources
        .map((entry) => entry.type.trim())
        .filter((entry) => entry.length > 0),
    ),
  );
}

export function deriveContextActorLabel(payload: ContextQueryResponse, campaign: CampaignSnapshot): string {
  if (payload.actor) {
    const partyEntry = campaign.party_overview.find((entry) => entry.slot_id === payload.actor);
    return partyEntry?.display_name || payload.actor;
  }
  return campaign.viewer_context.display_name || "Unknown actor";
}

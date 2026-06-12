import type { CampaignSnapshot } from "../../shared/api/contracts";
import { partyOverview, viewerClaimedSlotId } from "./partyHudModel";

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

/**
 * Singleplayer-Grundsatz: Der Spieler kontrolliert ausschließlich den eigenen
 * Charakter. Fremde Charaktere sind nur ansehbar. Eine spätere Ability kann
 * Kontrolle gewähren, indem sie die Viewer-Player-ID in
 * state.characters[slot].control_granted_to einträgt.
 */
export function canControlActor(campaign: CampaignSnapshot, slot_id: string | null | undefined): boolean {
  if (!slot_id) {
    return false;
  }
  if (viewerClaimedSlotId(campaign) === slot_id) {
    return true;
  }
  const viewerId = campaign.viewer_context?.player_id ?? "";
  if (!viewerId) {
    return false;
  }
  const character = readRecord(readRecord(readRecord(campaign.state).characters)[slot_id]);
  const grants = Array.isArray(character.control_granted_to) ? character.control_granted_to : [];
  return grants.includes(viewerId);
}

export function controllableActorIds(campaign: CampaignSnapshot): string[] {
  return partyOverview(campaign)
    .map((entry) => entry.slot_id)
    .filter((slot_id) => canControlActor(campaign, slot_id));
}

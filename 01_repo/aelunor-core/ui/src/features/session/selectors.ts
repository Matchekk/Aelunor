import type { SessionBootstrap } from "../../app/bootstrap/sessionStorage";
import type { CampaignSnapshot, SessionLibraryEntry } from "../../shared/api/contracts";
import { formatDateTime } from "../../shared/formatting/locale";

export function normalizeJoinCode(value: string): string {
  return value.toUpperCase().replace(/\s+/g, "").trim();
}

export function validateJoinInput(join_code: string, display_name: string): string | null {
  const normalizedJoinCode = normalizeJoinCode(join_code);
  const normalizedDisplayName = display_name.trim();

  if (!normalizedJoinCode) {
    return "Join code is required.";
  }
  if (normalizedJoinCode.length < 4) {
    return "Join code must be at least 4 characters.";
  }
  if (!normalizedDisplayName) {
    return "Display name is required.";
  }
  return null;
}

export function formatUpdatedAtLabel(value: string): string {
  const formatted = formatDateTime(value);
  if (!formatted) {
    return "Unknown";
  }
  return formatted;
}

export function deriveSessionSubtitle(entry: SessionLibraryEntry): string {
  const subtitleParts = [entry.join_code ? `Code ${entry.join_code}` : "No join code"];
  if (entry.campaign_title && entry.campaign_title !== entry.label) {
    subtitleParts.unshift(entry.campaign_title);
  }
  if (entry.display_name) {
    subtitleParts.push(entry.display_name);
  }
  subtitleParts.push(`Updated ${formatUpdatedAtLabel(entry.updated_at)}`);
  return subtitleParts.join(" • ");
}

export function toSessionBootstrap(entry: SessionLibraryEntry): SessionBootstrap {
  return {
    campaign_id: entry.campaign_id,
    player_id: entry.player_id,
    player_token: entry.player_token,
    join_code: entry.join_code || null,
  };
}

export function hasActiveSession(session: SessionBootstrap): boolean {
  return Boolean(session.campaign_id && session.player_id && session.player_token);
}

export function deriveNextWorkspaceHint(campaign: CampaignSnapshot): string {
  const viewer = campaign.viewer_context;
  if (viewer.needs_world_setup) {
    return "World setup would be the next gated destination in Phase C.";
  }
  if (viewer.needs_character_setup) {
    return "Character setup would be the next gated destination in Phase C.";
  }
  if (!viewer.claimed_slot_id) {
    return "Claim workspace would be the next gated destination in Phase C.";
  }
  return "Campaign play would be the next gated destination in Phase C.";
}

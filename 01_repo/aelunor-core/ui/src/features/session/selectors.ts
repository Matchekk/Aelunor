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
    return "Der Beitrittscode fehlt.";
  }
  if (normalizedJoinCode.length < 4) {
    return "Der Beitrittscode muss mindestens 4 Zeichen lang sein.";
  }
  if (!normalizedDisplayName) {
    return "Dein Name fehlt.";
  }
  return null;
}

export function formatUpdatedAtLabel(value: string): string {
  const formatted = formatDateTime(value);
  if (!formatted) {
    return "Unbekannt";
  }
  return formatted;
}

export function deriveSessionSubtitle(entry: SessionLibraryEntry): string {
  const subtitleParts = [entry.join_code ? `Code ${entry.join_code}` : "Kein Beitrittscode"];
  if (entry.campaign_title && entry.campaign_title !== entry.label) {
    subtitleParts.unshift(entry.campaign_title);
  }
  if (entry.display_name) {
    subtitleParts.push(entry.display_name);
  }
  subtitleParts.push(`Aktualisiert ${formatUpdatedAtLabel(entry.updated_at)}`);
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
    return "Das Welt-Setup ist der nächste gesperrte Schritt.";
  }
  if (viewer.needs_character_setup) {
    return "Das Charakter-Setup ist der nächste gesperrte Schritt.";
  }
  if (!viewer.claimed_slot_id) {
    return "Der Claim-Bereich ist der nächste gesperrte Schritt.";
  }
  return "Der Spieltisch ist der nächste gesperrte Schritt.";
}

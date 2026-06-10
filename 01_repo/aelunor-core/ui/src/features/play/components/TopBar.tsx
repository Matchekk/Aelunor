import { memo, useMemo, useRef, useState } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import type { SessionBootstrap } from "../../../app/bootstrap/sessionStorage";
import { SettingsDialog } from "../../../shared/ui/SettingsDialog";
import { useUserSettingsStore } from "../../../entities/settings/store";
import { derivePlayPhaseState } from "../selectors";

interface TopBarProps {
  campaign: CampaignSnapshot;
  session: SessionBootstrap;
  active_scene_label: string;
  active_actor_label: string;
  on_leave_session: () => void;
  can_unclaim: boolean;
  unclaim_pending: boolean;
  on_open_codex: () => void;
  on_open_notifications: () => void;
  on_unclaim: () => void;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export const TopBar = memo(function TopBar({
  campaign,
  session,
  active_scene_label,
  active_actor_label,
  on_leave_session,
  can_unclaim,
  unclaim_pending,
  on_open_codex,
  on_open_notifications,
  on_unclaim,
}: TopBarProps) {
  const confirmLeave = useUserSettingsStore((state) => state.interaction.confirm_leave);
  const phaseState = derivePlayPhaseState(campaign);
  const [copyLabel, setCopyLabel] = useState("Code:");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);

  const meta = useMemo(() => {
    const stateMeta = readRecord(readRecord(campaign.state).meta);
    const timing = readRecord(stateMeta.timing);
    const world = readRecord(readRecord(campaign.state).world);
    const settings = readRecord(world.settings);
    const campaignLengthRaw = readString(settings.campaign_length).trim().toLowerCase();
    const day = readNumber(campaign.world_time?.day);
    const timeOfDay = readString(campaign.world_time?.time_of_day).trim();
    const cycleSec = readNumber(timing.cycle_ema_sec);

    let campaignLengthLabel = "Kampagne";
    if (campaignLengthRaw === "open") {
      campaignLengthLabel = "Offen";
    } else if (campaignLengthRaw === "medium") {
      campaignLengthLabel = "Mittel";
    } else if (campaignLengthRaw === "short") {
      campaignLengthLabel = "Kurz";
    }

    return {
      phase: phaseState.phase_display || phaseState.phase,
      scene: active_scene_label && active_scene_label !== "Alle Szenen" ? active_scene_label : campaign.boards?.plot_essentials?.active_scene || "Alle Szenen",
      actor: active_actor_label,
      session: session.join_code ? "LIVE" : campaignLengthLabel,
      detail: [day !== null ? `Tag ${day}` : "", timeOfDay, cycleSec !== null ? `${Math.round(cycleSec)}s` : ""].filter(Boolean).join(" · "),
    };
  }, [
    active_actor_label,
    active_scene_label,
    campaign.boards?.plot_essentials?.active_scene,
    campaign.state,
    campaign.world_time?.day,
    campaign.world_time?.time_of_day,
    phaseState.phase,
    phaseState.phase_display,
    session.join_code,
  ]);

  const copyJoinCode = async () => {
    if (!session.join_code || !navigator.clipboard) {
      return;
    }
    try {
      await navigator.clipboard.writeText(session.join_code);
      setCopyLabel("Kopiert:");
      window.setTimeout(() => setCopyLabel("Code:"), 1200);
    } catch {
      setCopyLabel("Fehler:");
      window.setTimeout(() => setCopyLabel("Code:"), 1200);
    }
  };

  return (
    <header className="v1-topbar campaign-topbar command-bar topbar">
      <div className="campaign-topbar-brand">
        <img className="topbar-brand-icon" src="/v1/brand/aelunor-icon-512x512.png" alt="Aelunor" />
        <strong>Aelunor</strong>
      </div>

      <div className="campaign-topbar-meta" aria-label={campaign.campaign_meta.title || "Aelunor Kampagne"}>
        <div><span>Phase</span><strong>{meta.phase}</strong></div>
        <div><span>Szene</span><strong>{meta.scene}</strong></div>
        <div><span>Aktiver Slot</span><strong>{meta.actor}</strong></div>
        <div><span>Session</span><strong>{meta.session}</strong><small>{meta.detail}</small></div>
      </div>

      <div className="command-bar-right topbar-actions">
        {can_unclaim ? (
          <button type="button" className="topbar-utility-btn" onClick={on_unclaim} disabled={unclaim_pending}>
            {unclaim_pending ? "Loest..." : "Claim loesen"}
          </button>
        ) : null}
        {session.join_code ? (
          <button
            type="button"
            className="topbar-utility-btn topbar-code-button"
            onClick={() => void copyJoinCode()}
            title="Code kopieren"
          >
            {copyLabel} {session.join_code}
          </button>
        ) : null}
        <button
          type="button"
          className="topbar-utility-btn"
          onClick={() => {
            if (!confirmLeave || window.confirm("Aktive Sitzung lokal verlassen und zum Hub zurueckkehren?")) {
              on_leave_session();
            }
          }}
        >
          Hub
        </button>
        <button type="button" className="topbar-icon-action" onClick={on_open_codex} aria-label="Codex oeffnen" title="Codex">
          <span className="topbar-action-glyph is-book" aria-hidden="true" />
        </button>
        <button
          type="button"
          className="topbar-icon-action"
          onClick={on_open_notifications}
          aria-label="Benachrichtigungen oeffnen"
          title="Benachrichtigungen"
        >
          <span className="topbar-action-glyph is-bell" aria-hidden="true" />
        </button>
        <button
          ref={settingsButtonRef}
          type="button"
          className="topbar-icon-action"
          aria-label="Einstellungen oeffnen"
          onClick={() => setSettingsOpen(true)}
        >
          <span className="topbar-action-glyph is-gear" aria-hidden="true" />
        </button>
      </div>
      <SettingsDialog open={settingsOpen} on_close={() => setSettingsOpen(false)} return_focus_element={settingsButtonRef.current} />
    </header>
  );
});

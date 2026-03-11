import { memo, useMemo, useRef, useState } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import type { SessionBootstrap } from "../../../app/bootstrap/sessionStorage";
import { SettingsDialog } from "../../../shared/ui/SettingsDialog";
import { derivePlayPhaseState } from "../selectors";
import { useUserSettingsStore } from "../../../entities/settings/store";

interface TopBarProps {
  campaign: CampaignSnapshot;
  session: SessionBootstrap;
  active_scene_label: string;
  on_leave_session: () => void;
  can_unclaim: boolean;
  unclaim_pending: boolean;
  on_unclaim: () => void;
}

export const TopBar = memo(function TopBar({
  campaign,
  session,
  active_scene_label,
  on_leave_session,
  can_unclaim,
  unclaim_pending,
  on_unclaim,
}: TopBarProps) {
  const confirmLeave = useUserSettingsStore((state) => state.interaction.confirm_leave);

  const title = campaign.campaign_meta.title || "Unbenannte Kampagne";
  const phaseState = derivePlayPhaseState(campaign);

  const [copyLabel, setCopyLabel] = useState("Code:");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);

  const commandMetaLine = useMemo(() => {
    const readRecord = (value: unknown): Record<string, unknown> =>
      value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
    const readString = (value: unknown): string => (typeof value === "string" ? value : "");
    const readNumber = (value: unknown): number | null => (typeof value === "number" && Number.isFinite(value) ? value : null);

    const meta = readRecord(readRecord(campaign.state).meta);
    const timing = readRecord(meta.timing);
    const world = readRecord(readRecord(campaign.state).world);
    const settings = readRecord(world.settings);

    const turn = readNumber(meta.turn) ?? 0;
    const day = readNumber(campaign.world_time.day);
    const timeOfDay = readString(campaign.world_time.time_of_day).trim();
    const campaignLengthRaw = readString(settings.campaign_length).trim().toLowerCase();
    const cycleSec = readNumber(timing.cycle_ema_sec);

    let campaignLengthLabel = "Kampagne";
    if (campaignLengthRaw === "open") {
      campaignLengthLabel = "Offene Kampagne";
    } else if (campaignLengthRaw === "medium") {
      campaignLengthLabel = "Mittlere Kampagne";
    } else if (campaignLengthRaw === "short") {
      campaignLengthLabel = "Kurze Kampagne";
    }

    const parts = [`Turn ${turn}`, phaseState.phase_display || phaseState.phase];
    if (day !== null) {
      parts.push(`Tag ${day}`);
    }
    if (timeOfDay) {
      parts.push(timeOfDay.toUpperCase());
    }
    parts.push(campaignLengthLabel);
    if (cycleSec !== null) {
      parts.push(`Ø Zyklus ${Math.round(cycleSec)}s`);
    }

    if (active_scene_label && active_scene_label !== "Alle Szenen") {
      parts.push(`Szene ${active_scene_label}`);
    }

    return parts.join(" • ").toUpperCase();
  }, [active_scene_label, campaign.state, campaign.world_time.day, campaign.world_time.time_of_day, phaseState.phase, phaseState.phase_display]);

  const copyJoinCode = async () => {
    if (!session.join_code || !navigator.clipboard) {
      return;
    }
    try {
      await navigator.clipboard.writeText(session.join_code);
      setCopyLabel("Kopiert:");
      window.setTimeout(() => {
        setCopyLabel("Code:");
      }, 1200);
    } catch {
      setCopyLabel("Fehler:");
      window.setTimeout(() => {
        setCopyLabel("Code:");
      }, 1200);
    }
  };

  return (
    <header className="v1-topbar command-bar topbar">
      <div className="v1-topbar-block command-bar-left">
        <div className="v1-topbar-kicker topbar-brand">
          <img className="topbar-brand-icon" src="/static/brand/aelunor-icon-512x512.png" alt="Aelunor" />
          <span>Aelunor</span>
        </div>
        <h1 className="v1-topbar-title title">{title}</h1>
        <p className="command-bar-meta-line">{commandMetaLine}</p>
      </div>

      <div className="command-bar-right topbar-actions">
        {session.join_code ? (
          <button
            type="button"
            className="status-pill join-chip topbar-code-button"
            onClick={() => {
              void copyJoinCode();
            }}
            title="Code kopieren"
          >
            {copyLabel} {session.join_code}
          </button>
        ) : null}
        {can_unclaim ? (
          <button type="button" className="topbar-utility-btn" onClick={on_unclaim} disabled={unclaim_pending}>
            {unclaim_pending ? "Claim wird gelöst..." : "Claim lösen"}
          </button>
        ) : null}
        <button
          type="button"
          className="topbar-utility-btn"
          onClick={() => {
            if (!confirmLeave || window.confirm("Aktive Sitzung lokal verlassen und zum Hub zurückkehren?")) {
              on_leave_session();
            }
          }}
        >
          Session verlassen
        </button>
        <button
          ref={settingsButtonRef}
          type="button"
          className="menu-icon-button"
          aria-label="Einstellungen öffnen"
          onClick={() => {
            setSettingsOpen(true);
          }}
        >
          <span className="menu-icon-lines" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
        </button>
      </div>
      <SettingsDialog
        open={settingsOpen}
        on_close={() => {
          setSettingsOpen(false);
        }}
        return_focus_element={settingsButtonRef.current}
      />
    </header>
  );
});

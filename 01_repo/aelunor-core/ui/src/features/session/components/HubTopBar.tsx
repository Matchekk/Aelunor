import { useRef, useState } from "react";

import { SettingsDialog } from "../../../shared/ui/SettingsDialog";

interface HubTopBarProps {
  session_count: number;
  has_active_session: boolean;
  campaign_title?: string | null;
}

export function HubTopBar({ session_count, has_active_session, campaign_title = null }: HubTopBarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);

  return (
    <header className="hub-topbar">
      <div className="hub-topbar-brand">
        <div className="hub-topbar-kicker">
          <span className="hub-brand-badge" aria-hidden="true">
            <img className="hub-brand-icon" src="/brand/aelunor-icon-512x512.png" alt="" />
          </span>
        </div>
        <div className="hub-topbar-title">
          <span className="hub-brand-word">{campaign_title ? "Current Campaign" : "Aelunor"}</span>
          <h1>{campaign_title ?? "Campaign Hub"}</h1>
          <p>Campaign Control</p>
        </div>
      </div>
      <div className="hub-topbar-meta">
        <span className={`hub-status-badge${has_active_session ? " is-active" : ""}`}>
          {has_active_session ? "Session Active" : "Keine aktive Session"}
        </span>
        <span className="hub-resource-pill">
          <span aria-hidden="true" />
          {session_count} Sessions
        </span>
        <span className="hub-resource-pill">
          <span aria-hidden="true" />
          Runestones
        </span>
        <button type="button" className="hub-icon-button" aria-label="Benachrichtigungen">
          <span aria-hidden="true">N</span>
        </button>
        <button
          ref={settingsButtonRef}
          type="button"
          className="hub-profile-button"
          aria-label="Einstellungen öffnen"
          onClick={() => {
            setSettingsOpen(true);
          }}
        >
          <span className="hub-profile-orb" aria-hidden="true">
            <img src="/brand/aelunor-icon-512x512.png" alt="" />
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
}

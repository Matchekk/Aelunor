import { useRef, useState } from "react";

import { SettingsDialog } from "../../../shared/ui/SettingsDialog";

interface HubTopBarProps {
  session_count: number;
  has_active_session: boolean;
}

export function HubTopBar({ session_count, has_active_session }: HubTopBarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);

  return (
    <header className="v1-panel hub-topbar">
      <div className="hub-topbar-brand">
        <div className="hub-topbar-kicker">
          <span className="hub-brand-badge" aria-hidden="true">
            <img className="hub-brand-icon" src="/static/brand/aelunor-icon-512x512.png" alt="" />
          </span>
          <span className="hub-brand-word">Aelunor</span>
        </div>
        <h1>Campaign Hub</h1>
        <p>Fortsetzen, neue Kampagne starten oder per Code beitreten.</p>
      </div>
      <div className="hub-topbar-meta">
        <span className="status-pill">{session_count} gespeicherte Sessions</span>
        <span className="status-pill">{has_active_session ? "Aktive Session erkannt" : "Keine aktive Session"}</span>
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
}

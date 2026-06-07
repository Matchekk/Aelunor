import { useRef } from "react";

interface HubTopBarProps {
  session_count: number;
  has_active_session: boolean;
  on_open_settings: (return_focus_element: HTMLElement | null) => void;
}

export function HubTopBar({
  session_count,
  has_active_session,
  on_open_settings,
}: HubTopBarProps) {
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);

  return (
    <header className="hub-topbar" aria-label="Hub Status">
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
            on_open_settings(settingsButtonRef.current);
          }}
        >
          <span className="hub-profile-orb" aria-hidden="true">
            <img src="/v1/brand/aelunor-icon-512x512.png" alt="" />
          </span>
        </button>
      </div>
    </header>
  );
}

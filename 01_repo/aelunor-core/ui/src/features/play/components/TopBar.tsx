import { memo, useRef, useState } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import type { SessionBootstrap } from "../../../app/bootstrap/sessionStorage";
import { usePresenceStore } from "../../../entities/presence/store";
import { useLayoutStore } from "../../../state/layoutStore";
import { DisplaySettingsDialog } from "../../../shared/ui/DisplaySettingsDialog";
import type { SceneFilterId, SceneOption } from "../../scenes/selectors";
import { derivePresenceSummary, deriveViewerSummary } from "../selectors";

interface TopBarProps {
  campaign: CampaignSnapshot;
  session: SessionBootstrap;
  boards_novelty_label: string | null;
  selected_scene_id: SceneFilterId;
  scene_options: SceneOption[];
  on_scene_change: (scene_id: SceneFilterId) => void;
  on_open_boards: () => void;
  on_go_hub: () => void;
  on_leave_session: () => void;
  can_unclaim: boolean;
  unclaim_pending: boolean;
  on_unclaim: () => void;
}

export const TopBar = memo(function TopBar({
  campaign,
  session,
  boards_novelty_label,
  selected_scene_id,
  scene_options,
  on_scene_change,
  on_open_boards,
  on_go_hub,
  on_leave_session,
  can_unclaim,
  unclaim_pending,
  on_unclaim,
}: TopBarProps) {
  const rightRailOpen = useLayoutStore((state) => state.rightRailOpen);
  const toggleRightRail = useLayoutStore((state) => state.toggleRightRail);

  const title = campaign.campaign_meta.title || "Untitled campaign";
  const viewerSummary = deriveViewerSummary(campaign);
  const phase = campaign.viewer_context.phase || campaign.campaign_meta.status || "unknown";
  const selectedScene =
    scene_options.find((entry) => entry.scene_id === selected_scene_id)?.scene_name ??
    (selected_scene_id === "all" ? "All scenes" : selected_scene_id);
  const sseConnected = usePresenceStore((state) => state.sseConnected);
  const activities = usePresenceStore((state) => state.activities);
  const blockingAction = usePresenceStore((state) => state.blockingAction);
  const livePresenceSummary = derivePresenceSummary(sseConnected, activities, blockingAction);
  const [copyLabel, setCopyLabel] = useState("Copy code");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);

  const copyJoinCode = async () => {
    if (!session.join_code || !navigator.clipboard) {
      return;
    }
    try {
      await navigator.clipboard.writeText(session.join_code);
      setCopyLabel("Copied");
      window.setTimeout(() => setCopyLabel("Copy code"), 1200);
    } catch (_error) {
      setCopyLabel("Copy failed");
      window.setTimeout(() => setCopyLabel("Copy code"), 1200);
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
        <div className="command-bar-meta meta">
          <span>Phase {phase}</span>
          <span>{selectedScene}</span>
          <span>{viewerSummary}</span>
          {session.join_code ? <span>Code {session.join_code}</span> : null}
        </div>
      </div>

      <div className="command-bar-center" role="tablist" aria-label="Scene and thread context">
        {scene_options.map((option) => (
          <button
            key={option.scene_id}
            type="button"
            className={option.scene_id === selected_scene_id ? "command-scene-chip is-active" : "command-scene-chip"}
            onClick={() => on_scene_change(option.scene_id)}
            aria-pressed={option.scene_id === selected_scene_id}
          >
            <span>{option.scene_name}</span>
            <small>{option.member_count}</small>
          </button>
        ))}
      </div>

      <div className="command-bar-right topbar-actions">
        <div className="command-utility-row">
          {session.join_code ? <span className="status-pill join-chip">Code: {session.join_code}</span> : null}
          {session.join_code ? (
            <button type="button" className="btn ghost" onClick={() => void copyJoinCode()}>
              {copyLabel}
            </button>
          ) : null}
          <span className={sseConnected ? "status-pill connected" : "status-pill disconnected"}>
            {sseConnected ? "Live sync" : "Reconnecting"}
          </span>
          <span className="status-muted">{livePresenceSummary}</span>
          {blockingAction ? <span className="status-pill warning">{blockingAction.label}</span> : null}
        </div>
        <div className="command-actions-row">
          <button type="button" className="btn ghost" onClick={on_go_hub}>
            Hub
          </button>
          <button
            type="button"
            className="btn ghost"
            onClick={() => {
              if (window.confirm("Aktive Session lokal verlassen und zurück zum Hub?")) {
                on_leave_session();
              }
            }}
          >
            Session verlassen
          </button>
          {can_unclaim ? (
            <button type="button" className="btn ghost" onClick={on_unclaim} disabled={unclaim_pending}>
              {unclaim_pending ? "Claim lösen..." : "Claim lösen"}
            </button>
          ) : null}
          <button type="button" className="btn ghost" onClick={on_open_boards}>
            Boards{boards_novelty_label ? ` ${boards_novelty_label}` : ""}
          </button>
          <button type="button" className="btn ghost" onClick={toggleRightRail}>
            {rightRailOpen ? "Hide HUD" : "Show HUD"}
          </button>
          <button
            ref={settingsButtonRef}
            type="button"
            className="btn ghost"
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
      </div>
      <DisplaySettingsDialog
        open={settingsOpen}
        on_close={() => {
          setSettingsOpen(false);
        }}
        return_focus_element={settingsButtonRef.current}
      />
    </header>
  );
});

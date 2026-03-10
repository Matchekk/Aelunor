import { memo } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import type { SessionBootstrap } from "../../../app/bootstrap/sessionStorage";
import type { FontPresetId, FontSizeId, ThemeId } from "../../../shared/types/domain";
import { usePresenceStore } from "../../../entities/presence/store";
import { useLayoutStore } from "../../../state/layoutStore";
import { useThemeStore } from "../../../entities/theme/store";
import { derivePresenceSummary, deriveTopBarMeta, deriveViewerSummary } from "../selectors";

interface TopBarProps {
  campaign: CampaignSnapshot;
  session: SessionBootstrap;
  boards_novelty_label: string | null;
  on_open_boards: () => void;
}

export const TopBar = memo(function TopBar({ campaign, session, boards_novelty_label, on_open_boards }: TopBarProps) {
  const rightRailOpen = useLayoutStore((state) => state.rightRailOpen);
  const toggleRightRail = useLayoutStore((state) => state.toggleRightRail);

  const theme = useThemeStore((state) => state.theme);
  const fontPreset = useThemeStore((state) => state.font_preset);
  const fontSize = useThemeStore((state) => state.font_size);
  const setTheme = useThemeStore((state) => state.setTheme);
  const setFontPreset = useThemeStore((state) => state.setFontPreset);
  const setFontSize = useThemeStore((state) => state.setFontSize);

  const title = campaign.campaign_meta.title || "Untitled campaign";
  const viewerSummary = deriveViewerSummary(campaign);
  const metaItems = deriveTopBarMeta(campaign, session.join_code);
  const sseConnected = usePresenceStore((state) => state.sseConnected);
  const activities = usePresenceStore((state) => state.activities);
  const blockingAction = usePresenceStore((state) => state.blockingAction);
  const livePresenceSummary = derivePresenceSummary(sseConnected, activities, blockingAction);

  return (
    <header className="v1-topbar">
      <div className="v1-topbar-block">
        <div className="v1-topbar-kicker">Aelunor v1</div>
        <h1 className="v1-topbar-title">{title}</h1>
        <div className="v1-topbar-meta">
          {metaItems.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
        <div className="v1-topbar-meta">
          <span>{viewerSummary}</span>
          <span>Campaign {campaign.campaign_meta.campaign_id}</span>
          <span>{livePresenceSummary}</span>
        </div>
      </div>
      <div className="v1-topbar-controls">
        <label>
          Theme
          <select
            value={theme}
            onChange={(event) => {
              setTheme(event.target.value as ThemeId);
            }}
          >
            <option value="arcane">arcane</option>
            <option value="tavern">tavern</option>
            <option value="glade">glade</option>
            <option value="hybrid">hybrid</option>
          </select>
        </label>
        <label>
          Font
          <select
            value={fontPreset}
            onChange={(event) => {
              setFontPreset(event.target.value as FontPresetId);
            }}
          >
            <option value="classic">classic</option>
            <option value="clean">clean</option>
            <option value="literary">literary</option>
          </select>
        </label>
        <label>
          Size
          <select
            value={fontSize}
            onChange={(event) => {
              setFontSize(event.target.value as FontSizeId);
            }}
          >
            <option value="small">small</option>
            <option value="medium">medium</option>
            <option value="large">large</option>
          </select>
        </label>
        <button type="button" onClick={toggleRightRail}>
          {rightRailOpen ? "Hide Rail" : "Show Rail"}
        </button>
        <button type="button" onClick={on_open_boards}>
          Boards
          {boards_novelty_label ? ` ${boards_novelty_label}` : ""}
        </button>
      </div>
    </header>
  );
});

import { memo, useMemo } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import { FantasyPanel, StatusBadge } from "../../../shared/ui/fantasy/FantasyChrome";

interface WorldStatePanelProps {
  campaign: CampaignSnapshot;
  scene_label: string;
}

interface WorldStateSummary {
  threat: string;
  goal: string;
  turn: number;
  phase: string;
  canon_mode: string;
  weather: string;
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

export function deriveWorldStateSummary(campaign: CampaignSnapshot): WorldStateSummary {
  const state = readRecord(campaign.state);
  const meta = readRecord(state.meta);
  const canon = readRecord(state.canon);
  const patch = readRecord(state.patch_state);

  return {
    threat: readString(campaign.boards.plot_essentials.current_threat) || "Noch keine Bedrohung markiert",
    goal: readString(campaign.boards.plot_essentials.current_goal) || "Noch kein Ziel festgelegt",
    turn: readNumber(meta.turn) ?? campaign.active_turns.length,
    phase: readString(meta.phase) || campaign.viewer_context.phase || campaign.campaign_meta.status,
    canon_mode: readString(canon.mode) || readString(patch.mode) || "Balanced",
    weather: campaign.world_time.weather || campaign.world_time.time_of_day || "Unbekannt",
  };
}

export const WorldStatePanel = memo(function WorldStatePanel({ campaign, scene_label }: WorldStatePanelProps) {
  const worldState = useMemo(() => deriveWorldStateSummary(campaign), [campaign]);

  return (
    <FantasyPanel title="Scene & World" meta={scene_label} className="world-state-panel">
      <div className="world-state-hero">
        <div>
          <strong>{scene_label}</strong>
          <span>{worldState.weather}</span>
        </div>
        <StatusBadge label={worldState.phase} tone={worldState.phase === "active" ? "success" : "arcane"} />
      </div>
      <dl className="world-state-grid">
        <div>
          <dt>Turn</dt>
          <dd>{worldState.turn}</dd>
        </div>
        <div>
          <dt>Canon</dt>
          <dd>{worldState.canon_mode}</dd>
        </div>
      </dl>
      <div className="world-objective-list">
        <article>
          <span>Ziel</span>
          <p>{worldState.goal}</p>
        </article>
        <article>
          <span>Bedrohung</span>
          <p>{worldState.threat}</p>
        </article>
      </div>
    </FantasyPanel>
  );
});

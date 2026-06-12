import { memo, useMemo } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import { AelunorPanelFrame } from "../../../shared/ui/aelunorAssets";
import { displayParty, partyOverview, plotEssentials } from "../partyHudModel";
import { deriveSceneAtmosphere } from "../sceneAtmosphere";

interface WorldRailProps {
  campaign: CampaignSnapshot;
  active_scene_label: string;
  selected_actor_id: string | null;
  on_select_actor: (slot_id: string) => void;
  on_open_scene: () => void;
  on_open_quest: () => void;
  on_open_map: () => void;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function firstInitial(value: string): string {
  return value.trim().charAt(0).toUpperCase() || "?";
}

export const WorldRail = memo(function WorldRail({
  campaign,
  active_scene_label,
  selected_actor_id,
  on_select_actor,
  on_open_scene,
  on_open_quest,
  on_open_map,
}: WorldRailProps) {
  const scene = useMemo(() => deriveSceneAtmosphere(campaign, active_scene_label), [active_scene_label, campaign]);
  const plot = plotEssentials(campaign);
  const currentGoal = readString(plot.current_goal);
  const currentThreat = readString(plot.current_threat);
  const overview = partyOverview(campaign);
  const party = overview.length > 0 ? overview : displayParty(campaign).map((entry) => ({ ...entry }));
  const openLoops = (Array.isArray(plot.open_loops) ? plot.open_loops : []).filter(
    (entry): entry is string => typeof entry === "string" && entry.length > 0,
  );

  return (
    <aside className="world-rail" aria-label="Welt und Szene">
      <AelunorPanelFrame as="section" className="scene-card" variant="compact" texture>
        <button type="button" className="scene-card-button" onClick={on_open_scene}>
          <span className="play-panel-kicker">Szene</span>
          <span className="scene-image-slot" aria-hidden="true">
            <i />
          </span>
          <strong>{scene.name}</strong>
          <p className="scene-atmosphere">{scene.text}</p>
        </button>
      </AelunorPanelFrame>

      <AelunorPanelFrame as="section" className="current-quest-card" variant="compact" texture>
        <button type="button" className="quest-card-button" onClick={on_open_quest}>
          <span className="play-panel-kicker">Aktuelle Quest</span>
          <strong>{currentGoal || "Aktuelles Ziel noch offen"}</strong>
          {currentThreat ? <small>{currentThreat}</small> : <small>Keine akute Bedrohung markiert</small>}
          {openLoops.length > 0 ? (
            <span className="quest-loop-summary">{openLoops.slice(0, 2).join(" · ")}</span>
          ) : (
            <span className="quest-loop-summary">Keine offenen Schleifen</span>
          )}
        </button>
      </AelunorPanelFrame>

      <AelunorPanelFrame as="section" className="party-mini-panel" variant="compact" texture>
        <div className="play-panel-head">
          <span className="play-panel-kicker">Party</span>
          <small>{party.length} Akteure</small>
        </div>
        <div className="party-avatar-row">
          {party.length === 0 ? <p className="status-muted">Noch keine Party sichtbar.</p> : null}
          {party.slice(0, 5).map((entry) => {
            const slotId = entry.slot_id;
            const hpCurrent = "hp_current" in entry && typeof entry.hp_current === "number" ? entry.hp_current : null;
            const hpMax = "hp_max" in entry && typeof entry.hp_max === "number" ? entry.hp_max : null;
            const percent = hpMax && hpMax > 0 && hpCurrent !== null ? Math.max(0, Math.min(100, (hpCurrent / hpMax) * 100)) : null;
            return (
              <button
                key={slotId}
                type="button"
                className={selected_actor_id === slotId ? "party-avatar is-selected" : "party-avatar"}
                onClick={() => on_select_actor(slotId)}
                title={percent !== null ? `${entry.display_name} · ${hpCurrent}/${hpMax} Leben` : entry.display_name}
              >
                <span>{firstInitial(entry.display_name)}</span>
                {percent !== null ? <i style={{ width: `${percent}%` }} aria-hidden="true" /> : null}
              </button>
            );
          })}
        </div>
      </AelunorPanelFrame>

      <AelunorPanelFrame as="section" className="map-preview-card" variant="compact" texture>
        <button type="button" className="map-preview-button" onClick={on_open_map}>
          <span className="play-panel-kicker">Karte</span>
          <span className="map-placeholder" aria-hidden="true">
            <i className="map-river" />
            <i className="map-route one" />
            <i className="map-route two" />
            <i className="map-node one" />
            <i className="map-node two" />
            <i className="map-node three" />
            <i className="map-current" />
          </span>
          <span className="map-expand-glyph" aria-hidden="true" />
        </button>
      </AelunorPanelFrame>
    </aside>
  );
});

import { memo, useMemo, useState } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import { deriveCodexPreview, deriveNpcPreview } from "../../drawers/selectors";
import { deriveSceneMembership } from "../../scenes/selectors";

interface RightRailProps {
  campaign: CampaignSnapshot;
  selected_scene_id: string;
  on_open_character: (slot_id: string, tab_id?: string) => void;
  on_open_npc: (npc_id: string, tab_id?: string) => void;
  on_open_codex: (kind: "race" | "beast", entity_id: string, tab_id?: string) => void;
}

type RailTabId = "codex" | "diary" | "map" | "events";

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export const RightRail = memo(function RightRail({
  campaign,
  selected_scene_id,
  on_open_character,
  on_open_npc,
  on_open_codex,
}: RightRailProps) {
  const [activeTab, setActiveTab] = useState<RailTabId>("codex");
  const partyPreview = campaign.party_overview.slice(0, 6);
  const npcPreview = deriveNpcPreview(campaign);
  const codexPreview = deriveCodexPreview(campaign);
  const sceneMembers = useMemo(
    () => deriveSceneMembership(campaign, selected_scene_id).slice(0, 8),
    [campaign, selected_scene_id],
  );
  const sceneLabel =
    selected_scene_id === "all"
      ? "All scenes"
      : sceneMembers[0]?.scene_name || campaign.party_overview.find((entry) => entry.scene_id === selected_scene_id)?.scene_name || selected_scene_id;
  const recentEvents = useMemo(() => {
    const state = readRecord(campaign.state);
    const rawEvents = Array.isArray(state.events) ? state.events.filter((entry): entry is string => typeof entry === "string") : [];
    if (rawEvents.length > 0) {
      return rawEvents.slice(-8).reverse();
    }
    return campaign.active_turns
      .slice(-8)
      .reverse()
      .map((turn) => `Turn ${turn.turn_number}: ${turn.actor_display || turn.actor} (${turn.mode || turn.action_type})`);
  }, [campaign.active_turns, campaign.state]);

  return (
    <aside className="v1-panel right-rail hud-surface panel sidebar-column">
      <div className="v1-panel-head">
        <h2 className="panelTitle">Party</h2>
        <span>{campaign.party_overview.length} party</span>
      </div>
      <section className="right-rail-section party-panel">
        {partyPreview.length === 0 ? (
          <p className="status-muted">No party snapshot available yet.</p>
        ) : (
          <ul className="rail-list tactical-party-list party-overview">
            {partyPreview.map((entry) => (
              <li key={entry.slot_id} className="rail-list-item tactical-party-item party-card">
                <div className="tactical-party-head party-card-head">
                  <button type="button" className="rail-inline-button party-card-name" onClick={() => on_open_character(entry.slot_id)}>
                    {entry.display_name}
                  </button>
                  <span className="status-pill party-class-badge">{entry.class_name || "No class"}</span>
                </div>
                <div className="tactical-party-meta party-card-meta">
                  <span>{entry.resource_name || "Res"} {entry.res_current ?? 0}/{entry.res_max ?? 0}</span>
                  <span>{entry.scene_name || "No scene"}</span>
                  {entry.in_combat ? <span className="status-pill warning">Combat</span> : null}
                </div>
                {entry.conditions && entry.conditions.length > 0 ? (
                  <div className="tactical-party-conditions condition-pills">
                    {entry.conditions.slice(0, 3).map((condition) => (
                      <span key={condition} className="status-pill">
                        {condition}
                      </span>
                    ))}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
      <div className="rail-tab-row sidebar-tabs" role="tablist" aria-label="Sidebar views">
        <button type="button" role="tab" className={activeTab === "codex" ? "is-active tab" : "tab"} onClick={() => setActiveTab("codex")}>
          Kodex
        </button>
        <button type="button" role="tab" className={activeTab === "diary" ? "is-active tab" : "tab"} onClick={() => setActiveTab("diary")}>
          Diary
        </button>
        <button type="button" role="tab" className={activeTab === "map" ? "is-active tab" : "tab"} onClick={() => setActiveTab("map")}>
          Karte
        </button>
        <button type="button" role="tab" className={activeTab === "events" ? "is-active tab" : "tab"} onClick={() => setActiveTab("events")}>
          Events
        </button>
      </div>
      {activeTab === "diary" ? (
        <section className="right-rail-section tabPanel">
          <p className="status-muted">Current context: {sceneLabel}</p>
          {sceneMembers.length === 0 ? (
            <p className="status-muted">No members are currently mapped to this scene.</p>
          ) : (
            <ul className="rail-list">
              {sceneMembers.map((member) => (
                <li key={member.slot_id} className="rail-list-item">
                  <button type="button" className="rail-inline-button" onClick={() => on_open_character(member.slot_id)}>
                    {member.display_name}
                  </button>
                  <span className="status-muted">{member.class_name || "No class"}</span>
                </li>
              ))}
            </ul>
          )}
          {npcPreview.length > 0 ? (
            <>
              <p className="status-muted">Known NPCs in play</p>
              <ul className="rail-list">
                {npcPreview.slice(0, 5).map((entry) => (
                  <li key={entry.npc_id} className="rail-list-item">
                    <button type="button" className="rail-inline-button" onClick={() => on_open_npc(entry.npc_id)}>
                      {entry.name}
                    </button>
                    <span className="status-muted">{entry.role_hint || "Unknown role"}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </section>
      ) : null}
      {activeTab === "map" ? (
        <section className="right-rail-section tabPanel">
          <p className="status-muted">Scene overview</p>
          {sceneMembers.length === 0 ? (
            <p className="status-muted">No scene mapping data available.</p>
          ) : (
            <ul className="rail-list">
              {sceneMembers.map((member) => (
                <li key={member.slot_id} className="rail-list-item">
                  <button type="button" className="rail-inline-button" onClick={() => on_open_character(member.slot_id)}>
                    {member.display_name}
                  </button>
                  <span className="status-muted">{member.scene_name || selected_scene_id}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
      {activeTab === "events" ? (
        <section className="right-rail-section tabPanel">
          {recentEvents.length === 0 ? (
            <p className="status-muted">No recent events available.</p>
          ) : (
            <ul className="rail-list">
              {recentEvents.map((eventText, index) => (
                <li key={`${index}-${eventText.slice(0, 28)}`} className="rail-list-item">
                  <span className="status-muted">{eventText}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
      {activeTab === "codex" ? (
        <section className="right-rail-section tabPanel">
          {codexPreview.length > 0 ? (
            <ul className="rail-list">
              {codexPreview.map((entry) => (
                <li key={`${entry.kind}-${entry.entity_id}`} className="rail-list-item">
                  <button type="button" className="rail-inline-button" onClick={() => on_open_codex(entry.kind, entry.entity_id)}>
                    {entry.name}
                  </button>
                  <span className="status-muted">
                    {entry.kind} • Wissen {entry.knowledge_level}/4
                  </span>
                  {entry.novelty_label ? <span className="status-pill warning">{entry.novelty_label}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="status-muted">Noch keine Kodex-Einträge entdeckt.</p>
          )}
        </section>
      ) : null}
    </aside>
  );
});

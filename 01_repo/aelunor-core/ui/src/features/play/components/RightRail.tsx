import { memo, useMemo, useState } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import { deriveUserFacingErrorMessage } from "../../../shared/errors/userFacing";
import { deriveCodexPreview, deriveNpcPreview } from "../../drawers/selectors";
import { usePatchPlayerDiaryMutation } from "../mutations";
import { deriveSceneMembership } from "../../scenes/selectors";
import { WorldStatePanel } from "./WorldStatePanel";

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

function codexKindLabel(kind: "race" | "beast"): string {
  return kind === "race" ? "Volk" : "Bestie";
}

export const RightRail = memo(function RightRail({
  campaign,
  selected_scene_id,
  on_open_character,
  on_open_npc,
  on_open_codex,
}: RightRailProps) {
  const [activeTab, setActiveTab] = useState<RailTabId>("codex");
  const [diaryDraft, setDiaryDraft] = useState<string | null>(null);
  const partyPreview = campaign.party_overview.slice(0, 6);
  const npcPreview = deriveNpcPreview(campaign);
  const codexPreview = deriveCodexPreview(campaign);
  const viewerPlayerId = campaign.viewer_context.player_id ?? null;
  const diaries = campaign.boards.player_diaries ?? {};
  const ownDiaryEntry = viewerPlayerId ? diaries[viewerPlayerId] ?? null : null;
  const ownDiaryContent = diaryDraft ?? ownDiaryEntry?.content ?? "";
  const diaryMutation = usePatchPlayerDiaryMutation(campaign.campaign_meta.campaign_id, viewerPlayerId);
  const diaryError = diaryMutation.isError
    ? deriveUserFacingErrorMessage(diaryMutation.error, "Das Tagebuch konnte nicht gespeichert werden.")
    : null;
  const sceneMembers = useMemo(
    () => deriveSceneMembership(campaign, selected_scene_id).slice(0, 8),
    [campaign, selected_scene_id],
  );
  const sceneLabel =
    selected_scene_id === "all"
      ? "Alle Szenen"
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
      .map((turn) => `Zug ${turn.turn_number}: ${turn.actor_display || turn.actor} (${turn.mode || turn.action_type})`);
  }, [campaign.active_turns, campaign.state]);
  const diaryEntries = useMemo(() => {
    return campaign.players.map((player) => {
      const entry = diaries[player.player_id];
      return {
        player_id: player.player_id,
        display_name: player.display_name,
        content: entry?.content ?? "",
        updated_at: entry?.updated_at ?? null,
        is_self: player.player_id === viewerPlayerId,
      };
    });
  }, [campaign.players, diaries, viewerPlayerId]);

  return (
    <aside className="v1-panel right-rail hud-surface panel sidebar-column">
      <div className="v1-panel-head">
        <h2 className="panelTitle">Taktik</h2>
        <span>{campaign.party_overview.length} in Gruppe</span>
      </div>
      <section className="right-rail-section party-panel">
        {partyPreview.length === 0 ? (
          <p className="status-muted">Noch kein Gruppenstatus verfügbar.</p>
        ) : (
          <ul className="rail-list tactical-party-list party-overview">
            {partyPreview.map((entry) => (
              <li key={entry.slot_id} className="rail-list-item tactical-party-item party-card">
                <div className="tactical-party-head party-card-head">
                  <button type="button" className="rail-inline-button party-card-name" onClick={() => on_open_character(entry.slot_id)}>
                    {entry.display_name}
                  </button>
                  <span className="status-pill party-class-badge">{entry.class_name || "Keine Klasse"}</span>
                </div>
                <div className="tactical-party-meta party-card-meta">
                  <span>{entry.resource_name || "Ressource"} {entry.res_current ?? 0}/{entry.res_max ?? 0}</span>
                  <span>{entry.scene_name || "Keine Szene"}</span>
                  {entry.in_combat ? <span className="status-pill warning">Kampf</span> : null}
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
      <WorldStatePanel campaign={campaign} scene_label={sceneLabel} />
      <div className="rail-tab-row sidebar-tabs" role="tablist" aria-label="Taktische Bereiche">
        <button type="button" role="tab" className={activeTab === "codex" ? "is-active tab" : "tab"} onClick={() => setActiveTab("codex")}>
          Kodex
        </button>
        <button type="button" role="tab" className={activeTab === "diary" ? "is-active tab" : "tab"} onClick={() => setActiveTab("diary")}>
          Szene
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
          <p className="status-muted">
            Jeder Spieler hat ein eigenes Tagebuch. Zeilen mit <code>//</code> bleiben lokal privat.
          </p>
          <div className="rail-diary-list">
            {diaryEntries.map((entry) => (
              <article key={entry.player_id} className={entry.is_self ? "rail-diary-card is-self" : "rail-diary-card"}>
                <div className="rail-diary-head">
                  <strong>{entry.display_name || "Spieler"}</strong>
                  <span className="status-pill">{entry.is_self ? "dein Tagebuch" : "read only"}</span>
                </div>
                {entry.is_self ? (
                  <>
                    <textarea
                      value={ownDiaryContent}
                      rows={4}
                      onChange={(event) => {
                        setDiaryDraft(event.target.value);
                      }}
                      disabled={diaryMutation.isPending || !viewerPlayerId}
                    />
                    <div className="session-inline-actions">
                      <button
                        type="button"
                        onClick={() => {
                          void diaryMutation.mutateAsync(
                            {
                              content: ownDiaryContent,
                            },
                            {
                              onSuccess: () => {
                                setDiaryDraft(null);
                              },
                            },
                          );
                        }}
                        disabled={diaryMutation.isPending || !viewerPlayerId}
                      >
                        {diaryMutation.isPending ? "Speichere..." : "Tagebuch speichern"}
                      </button>
                    </div>
                    {diaryError ? <p className="session-feedback error">{diaryError}</p> : null}
                  </>
                ) : (
                  <p className="status-muted">{entry.content || "Noch keine Notizen."}</p>
                )}
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {activeTab === "map" ? (
        <section className="right-rail-section tabPanel">
          <p className="status-muted">Szenenübersicht</p>
          {sceneMembers.length === 0 ? (
            <p className="status-muted">Keine Szenenzuordnung verfügbar.</p>
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
            <p className="status-muted">Keine aktuellen Ereignisse.</p>
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
                    {codexKindLabel(entry.kind)} • Wissen {entry.knowledge_level}/4
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

import { memo } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import type { SessionBootstrap } from "../../../app/bootstrap/sessionStorage";
import { deriveCodexPreview, deriveNpcPreview } from "../../drawers/selectors";
import { deriveRightRailItems } from "../selectors";

interface RightRailProps {
  campaign: CampaignSnapshot;
  session: SessionBootstrap;
  selected_scene_id: string;
  on_open_character: (slot_id: string, tab_id?: string) => void;
  on_open_npc: (npc_id: string, tab_id?: string) => void;
  on_open_codex: (kind: "race" | "beast", entity_id: string, tab_id?: string) => void;
}

export const RightRail = memo(function RightRail({
  campaign,
  session,
  selected_scene_id,
  on_open_character,
  on_open_npc,
  on_open_codex,
}: RightRailProps) {
  const metaItems = deriveRightRailItems(campaign);
  const partyPreview = campaign.party_overview.slice(0, 4);
  const npcPreview = deriveNpcPreview(campaign);
  const codexPreview = deriveCodexPreview(campaign);

  return (
    <aside className="v1-panel right-rail">
      <div className="v1-panel-head">
        <h2>Right Rail</h2>
        <span>read-only</span>
      </div>
      <dl className="meta-list">
        {metaItems.map((item) => (
          <div key={item.label}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
        <div>
          <dt>Join code</dt>
          <dd>{session.join_code ?? "n/a"}</dd>
        </div>
      </dl>
      <section className="right-rail-section">
        <div className="v1-panel-head">
          <h2>Party Preview</h2>
          <span>{campaign.party_overview.length}</span>
        </div>
        {partyPreview.length === 0 ? (
          <p className="status-muted">No party snapshot available yet.</p>
        ) : (
          <ul className="rail-list">
            {partyPreview.map((entry) => (
              <li key={entry.slot_id} className="rail-list-item">
                <button type="button" className="rail-inline-button" onClick={() => on_open_character(entry.slot_id)}>
                  {entry.display_name}
                </button>
                <span className="status-muted">
                  {entry.class_name || "No class"} {entry.scene_name ? `• ${entry.scene_name}` : ""}
                </span>
                {selected_scene_id !== "all" && entry.scene_id === selected_scene_id ? (
                  <span className="status-pill">Here</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="right-rail-section">
        <div className="v1-panel-head">
          <h2>Known NPCs</h2>
          <span>{npcPreview.length}</span>
        </div>
        {npcPreview.length > 0 ? (
          <ul className="rail-list">
            {npcPreview.map((entry) => (
              <li key={entry.npc_id} className="rail-list-item">
                <button type="button" className="rail-inline-button" onClick={() => on_open_npc(entry.npc_id)}>
                  {entry.name}
                </button>
                <span className="status-muted">
                  {entry.role_hint || "Unknown role"} {entry.scene_name ? `• ${entry.scene_name}` : ""}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="status-muted">No known NPC summary entries are available yet.</p>
        )}
      </section>
      <section className="right-rail-section">
        <div className="v1-panel-head">
          <h2>Codex</h2>
          <span>{codexPreview.length}</span>
        </div>
        {codexPreview.length > 0 ? (
          <ul className="rail-list">
            {codexPreview.map((entry) => (
              <li key={`${entry.kind}-${entry.entity_id}`} className="rail-list-item">
                <button type="button" className="rail-inline-button" onClick={() => on_open_codex(entry.kind, entry.entity_id)}>
                  {entry.name}
                </button>
                <span className="status-muted">
                  {entry.kind} • knowledge {entry.knowledge_level}/4
                </span>
                {entry.novelty_label ? <span className="status-pill warning">{entry.novelty_label}</span> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="status-muted">No codex entries have been discovered yet.</p>
        )}
      </section>
    </aside>
  );
});

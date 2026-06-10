import { memo, useMemo } from "react";

import type { CampaignSnapshot } from "../../../shared/api/contracts";
import { derivePartyHud, type UiCharacterSummary } from "../partyHudModel";

interface PartyStatusPanelProps {
  campaign: CampaignSnapshot;
  selected_slot_id: string | null;
  on_open_character: (slot_id: string, tab_id?: string) => void;
}

function ResourceRow({ label, text, percent, tone }: { label: string; text: string; percent: number | null; tone: string }) {
  return (
    <div className={`party-hud-meter is-${tone}`}>
      <span>{label}</span>
      <strong>{text}</strong>
      {percent !== null ? <i style={{ width: `${percent}%` }} aria-hidden="true" /> : null}
    </div>
  );
}

function PartyMemberCard({
  member,
  selected,
  on_open_character,
}: {
  member: UiCharacterSummary;
  selected: boolean;
  on_open_character: PartyStatusPanelProps["on_open_character"];
}) {
  return (
    <li className={selected ? "party-hud-card is-selected" : "party-hud-card"}>
      <div className="party-hud-head">
        <button type="button" className="party-hud-name" onClick={() => on_open_character(member.slot_id)}>
          {member.name}
          {member.is_viewer ? <small> (du)</small> : null}
        </button>
        {member.in_combat ? <span className="status-pill warning">Kampf</span> : null}
      </div>
      <p className="party-hud-class">
        {member.class_label}
        {member.level_label ? ` · ${member.level_label}` : ""}
      </p>
      <ResourceRow label="Leben" text={member.hp.text} percent={member.hp.percent} tone="hp" />
      <ResourceRow label="Ausdauer" text={member.stamina.text} percent={member.stamina.percent} tone="stamina" />
      <ResourceRow label={member.resource_name} text={member.resource.text} percent={member.resource.percent} tone="essence" />
      <p className="party-hud-meta">
        <span>{member.scene_label}</span>
        <span>Ruf: {member.karma_label}</span>
      </p>
      {member.conditions.length > 0 || member.injury_count > 0 ? (
        <p className="party-hud-conditions">
          {member.conditions.map((condition) => (
            <span key={condition} className="status-pill">
              {condition}
            </span>
          ))}
          {member.injury_count > 0 ? <span className="status-pill warning">{member.injury_count} Verletzungen</span> : null}
        </p>
      ) : null}
    </li>
  );
}

export const PartyStatusPanel = memo(function PartyStatusPanel({
  campaign,
  selected_slot_id,
  on_open_character,
}: PartyStatusPanelProps) {
  const hud = useMemo(() => derivePartyHud(campaign), [campaign]);

  return (
    <section className="actor-dock-section party-hud" aria-label="Party-Status">
      <div className="party-hud-panel-head">
        <span className="actor-dock-kicker">Party</span>
        <small>
          {hud.party_count} {hud.party_count === 1 ? "Mitglied" : "Mitglieder"} · {hud.phase_label}
        </small>
      </div>
      <p className="party-hud-scene">{hud.scene.label}</p>
      {hud.characters.length === 0 ? (
        <p className="status-muted">Noch keine Charaktere im Spiel.</p>
      ) : (
        <ul className="party-hud-list">
          {hud.characters.map((member) => (
            <PartyMemberCard
              key={member.slot_id}
              member={member}
              selected={member.slot_id === selected_slot_id}
              on_open_character={on_open_character}
            />
          ))}
        </ul>
      )}
    </section>
  );
});

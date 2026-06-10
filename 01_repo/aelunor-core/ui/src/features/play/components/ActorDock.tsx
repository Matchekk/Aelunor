import { memo, useMemo, useState, type ReactNode } from "react";

import { useQuery } from "@tanstack/react-query";

import type { CampaignSnapshot, CharacterSheetResponse } from "../../../shared/api/contracts";
import { endpoints } from "../../../shared/api/endpoints";
import { getJson } from "../../../shared/api/httpClient";
import { AelunorPanelFrame } from "../../../shared/ui/aelunorAssets";
import { deriveActorDockView, type ActorPanelSection, type ResourceMeter } from "../actorDockModel";

interface ActorDockProps {
  campaign: CampaignSnapshot;
  selected_slot_id: string | null;
  on_open_character: (slot_id: string, tab_id?: string) => void;
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "?";
}

function meterPercent(meter: ResourceMeter): number {
  if (!meter.max || meter.max <= 0 || meter.current === null) {
    return 0;
  }
  return Math.max(0, Math.min(100, (meter.current / meter.max) * 100));
}

function DockSection({
  id,
  label,
  active,
  on_select,
  children,
}: {
  id: ActorPanelSection;
  label: string;
  active: boolean;
  on_select: (id: ActorPanelSection) => void;
  children: ReactNode;
}) {
  return (
    <section className={`actor-dock-section is-${id}${active ? " is-selected" : ""}`}>
      <button type="button" className="actor-section-button" onClick={() => on_select(id)}>
        {label}
      </button>
      {children}
    </section>
  );
}

export const ActorDock = memo(function ActorDock({ campaign, selected_slot_id, on_open_character }: ActorDockProps) {
  const [selectedCharacterPanelSection, setSelectedCharacterPanelSection] = useState<ActorPanelSection>("overview");
  const query = useQuery({
    queryKey: ["play", "actor-dock", campaign.campaign_meta.campaign_id, selected_slot_id],
    queryFn: () => getJson<CharacterSheetResponse>(endpoints.campaigns.character_sheet(campaign.campaign_meta.campaign_id, selected_slot_id ?? "")),
    enabled: Boolean(selected_slot_id),
    retry: false,
  });

  const view = useMemo(
    () => (selected_slot_id ? deriveActorDockView(campaign, selected_slot_id, query.data ?? null) : null),
    [campaign, query.data, selected_slot_id],
  );

  if (!selected_slot_id || !view) {
    return (
      <AelunorPanelFrame as="aside" className="actor-dock" variant="compact" texture>
        <p className="status-muted">Noch kein Akteur ausgewaehlt.</p>
      </AelunorPanelFrame>
    );
  }

  return (
    <AelunorPanelFrame as="aside" className="actor-dock" variant="compact" texture>
      <header className="actor-header">
        <button type="button" className="actor-portrait-slot" onClick={() => on_open_character(selected_slot_id)}>
          <span>{initials(view.display_name)}</span>
          <i aria-hidden="true" />
        </button>
        <div className="actor-header-copy">
          <div>
            <p className="actor-dock-kicker">{view.active ? "Akteur aktiv" : "Akteur"}</p>
            <h2>{view.display_name}</h2>
          </div>
          <p>{view.species}</p>
          <p>
            {view.class_name} · {view.class_rank}
          </p>
          <p>
            Level {view.level ?? 1}
            {view.xp_current !== null || view.xp_to_next !== null ? ` · ${view.xp_current ?? 0}/${view.xp_to_next ?? "?"} XP` : ""}
          </p>
          <p className="actor-scene-line">{view.scene_label}</p>
        </div>
      </header>

      <DockSection id="resources" label="Ressourcen" active={selectedCharacterPanelSection === "resources"} on_select={setSelectedCharacterPanelSection}>
        <div className="resource-meters">
          {view.resources.map((meter) => (
            <div key={meter.key} className={`resource-meter is-${meter.tone}`}>
              <span>{meter.label}</span>
              <strong>
                {meter.current ?? "-"} / {meter.max ?? "-"}
              </strong>
              <i style={{ width: `${meterPercent(meter)}%` }} aria-hidden="true" />
            </div>
          ))}
        </div>
      </DockSection>

      <DockSection id="status" label="Status" active={selectedCharacterPanelSection === "status"} on_select={setSelectedCharacterPanelSection}>
        <div className="status-chips">
          {(view.conditions.length > 0 ? view.conditions.slice(0, 3) : ["Keine schweren Zustaende"]).map((condition) => (
            <span key={condition}>{condition}</span>
          ))}
          <span>{view.can_act_label}</span>
          <span>Ruf: {view.karma_label}</span>
          <span>{view.injury_count} Verletzungen</span>
          <span>{view.scar_count} Narben</span>
          {view.effects_count > 0 ? <span>{view.effects_count} Effekte</span> : null}
        </div>
      </DockSection>

      <DockSection id="body" label="Koerper & Druck" active={selectedCharacterPanelSection === "body"} on_select={setSelectedCharacterPanelSection}>
        <dl className="body-pressure-panel">
          <div><dt>Energie</dt><dd>{view.body_energy}</dd></div>
          <div><dt>Schmerz</dt><dd>{view.body_pain}</dd></div>
          <div><dt>Druck</dt><dd>{view.pressure}</dd></div>
        </dl>
      </DockSection>

      <DockSection id="skills" label="Top-Fertigkeiten" active={selectedCharacterPanelSection === "skills"} on_select={setSelectedCharacterPanelSection}>
        <div className="top-skills-panel">
          {view.skills.length === 0 ? <p>Noch keine Fertigkeiten entdeckt</p> : null}
          {view.skills.map((skill) => (
            <button key={skill.id} type="button" onClick={() => on_open_character(selected_slot_id, "skills")}>
              <span>{skill.name}</span>
              <strong>{skill.value}</strong>
            </button>
          ))}
        </div>
      </DockSection>

      <DockSection id="equipment" label="Ausruestung" active={selectedCharacterPanelSection === "equipment"} on_select={setSelectedCharacterPanelSection}>
        <div className="equipment-preview">
          {view.equipment.length === 0 ? <p>Keine Ausruestung sichtbar</p> : null}
          {view.equipment.map((item) => (
            <button key={`${item.slot}-${item.name}`} type="button" onClick={() => on_open_character(selected_slot_id, "gear")}>
              <span>{item.slot}</span>
              <strong>{item.name}</strong>
            </button>
          ))}
        </div>
      </DockSection>

      <DockSection id="inventory" label="Wichtige Gegenstaende" active={selectedCharacterPanelSection === "inventory"} on_select={setSelectedCharacterPanelSection}>
        <div className="important-items-panel">
          {view.items.length === 0 ? <p>Keine wichtigen Gegenstaende</p> : null}
          {view.items.map((item) => (
            <button key={item.id} type="button" onClick={() => on_open_character(selected_slot_id, "gear")}>
              {item.name}
            </button>
          ))}
        </div>
      </DockSection>

      <DockSection id="bonds" label="Beziehungen" active={selectedCharacterPanelSection === "bonds"} on_select={setSelectedCharacterPanelSection}>
        <div className="bonds-preview-panel">
          {view.bonds.length === 0 ? <p>Noch keine Bindungen entdeckt</p> : null}
          {view.bonds.map((bond) => (
            <button key={bond.id} type="button" onClick={() => on_open_character(selected_slot_id, "overview")}>
              <span>{bond.name}</span>
              <strong>{bond.detail}</strong>
            </button>
          ))}
          {view.factions.length > 0 ? <small>Fraktion: {view.factions.join(", ")}</small> : null}
        </div>
      </DockSection>

      {query.isError ? <p className="actor-dock-note">Detaildaten nicht geladen; zeige Gruppenstatus.</p> : null}
    </AelunorPanelFrame>
  );
});

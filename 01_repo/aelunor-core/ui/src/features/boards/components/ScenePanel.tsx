import type { CampaignSnapshot } from "../../../shared/api/contracts";
import { plotEssentials } from "../../play/partyHudModel";
import { deriveSceneAtmosphere } from "../../play/sceneAtmosphere";
import { deriveSceneMembership } from "../../scenes/selectors";

interface ScenePanelProps {
  campaign: CampaignSnapshot;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function ScenePanel({ campaign }: ScenePanelProps) {
  const activeSceneLabel = String(plotEssentials(campaign).active_scene ?? "");
  const atmosphere = deriveSceneAtmosphere(campaign, activeSceneLabel);
  const members = deriveSceneMembership(campaign, "all").filter(
    (member) => !member.scene_name || member.scene_name === atmosphere.name,
  );
  const nodes = readRecord(readRecord(readRecord(campaign.state).map).nodes);
  const node = Object.values(nodes)
    .map(readRecord)
    .find((entry) => String(entry.name ?? "") === atmosphere.name);
  const danger = typeof node?.danger === "number" ? node.danger : null;

  return (
    <section className="scene-panel">
      <h2>{atmosphere.name}</h2>
      <p className="scene-atmosphere">{atmosphere.text}</p>
      {danger !== null ? (
        <p className="status-muted">Gefahreneinschätzung: {danger} / 10</p>
      ) : null}
      <div className="v1-panel-head">
        <h3>Anwesende</h3>
        <span>{members.length}</span>
      </div>
      {members.length === 0 ? (
        <p className="status-muted">Niemand aus der Gruppe ist hier verzeichnet.</p>
      ) : (
        <ul className="scene-member-list">
          {members.map((member) => (
            <li key={member.slot_id}>
              <strong>{member.display_name}</strong>
              {member.class_name ? <span className="status-muted"> · {member.class_name}</span> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

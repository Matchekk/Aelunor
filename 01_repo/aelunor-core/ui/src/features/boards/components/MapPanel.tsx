import type { CampaignSnapshot } from "../../../shared/api/contracts";

interface MapPanelProps {
  campaign: CampaignSnapshot;
}

interface MapNodeView {
  id: string;
  name: string;
  type: string;
  danger: number | null;
  discovered: boolean;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function deriveMapNodes(campaign: CampaignSnapshot): MapNodeView[] {
  const nodes = readRecord(readRecord(readRecord(campaign.state).map).nodes);
  return Object.entries(nodes).map(([id, value]) => {
    const node = readRecord(value);
    return {
      id,
      name: String(node.name ?? id),
      type: String(node.type ?? ""),
      danger: typeof node.danger === "number" ? node.danger : null,
      discovered: node.discovered !== false,
    };
  });
}

function deriveMapEdges(campaign: CampaignSnapshot, nodeNames: Map<string, string>): string[] {
  const edges = readRecord(readRecord(campaign.state).map).edges;
  if (!Array.isArray(edges)) {
    return [];
  }
  return edges
    .map((value) => {
      const edge = readRecord(value);
      const from = nodeNames.get(String(edge.from ?? "")) ?? String(edge.from ?? "");
      const to = nodeNames.get(String(edge.to ?? "")) ?? String(edge.to ?? "");
      if (!from || !to) {
        return "";
      }
      const kind = String(edge.kind ?? "");
      return kind ? `${from} – ${to} (${kind})` : `${from} – ${to}`;
    })
    .filter(Boolean);
}

export function MapPanel({ campaign }: MapPanelProps) {
  const nodes = deriveMapNodes(campaign);
  const discovered = nodes.filter((node) => node.discovered);
  const hiddenCount = nodes.length - discovered.length;
  const nodeNames = new Map(nodes.map((node) => [node.id, node.name]));
  const edges = deriveMapEdges(campaign, nodeNames);

  return (
    <section className="map-panel">
      <div className="v1-panel-head">
        <h3>Bekannte Orte</h3>
        <span>{discovered.length}</span>
      </div>
      {discovered.length === 0 ? (
        <p className="status-muted">Noch keine Orte entdeckt. Die Karte füllt sich, während die Geschichte voranschreitet.</p>
      ) : (
        <ul className="map-node-list">
          {discovered.map((node) => (
            <li key={node.id}>
              <strong>{node.name}</strong>
              <span className="status-muted">
                {[node.type, node.danger !== null ? `Gefahr ${node.danger}/10` : ""].filter(Boolean).join(" · ")}
              </span>
            </li>
          ))}
        </ul>
      )}
      {hiddenCount > 0 ? <p className="status-muted">{hiddenCount} weitere Orte sind noch unentdeckt.</p> : null}
      {edges.length > 0 ? (
        <>
          <div className="v1-panel-head">
            <h3>Verbindungen</h3>
            <span>{edges.length}</span>
          </div>
          <ul className="map-edge-list">
            {edges.map((edge) => (
              <li key={edge} className="status-muted">
                {edge}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

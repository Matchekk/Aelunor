import type { NpcSheetResponse } from "../../../shared/api/contracts";

interface NpcDrawerProps {
  sheet: NpcSheetResponse;
  active_tab: string;
}

export function NpcDrawer({ sheet, active_tab }: NpcDrawerProps) {
  if (active_tab === "class") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Goal</strong>
          <p>{sheet.goal || "No primary goal recorded."}</p>
        </article>
        <article className="drawer-card">
          <strong>Backstory</strong>
          <p>{sheet.backstory_short || "No short backstory is available yet."}</p>
        </article>
      </section>
    );
  }

  if (active_tab === "attributes") {
    return (
      <section className="drawer-panel">
        <article className="drawer-card">
          <strong>History</strong>
          {(sheet.history_notes ?? []).length > 0 ? (
            <ul className="rail-list">
              {sheet.history_notes?.map((entry) => (
                <li key={entry} className="rail-list-item">
                  {entry}
                </li>
              ))}
            </ul>
          ) : (
            <p className="status-muted">No history notes are available yet.</p>
          )}
        </article>
      </section>
    );
  }

  if (active_tab === "skills") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Links</strong>
          <p>Faction: {sheet.faction || "None"}</p>
          <p>Role hint: {sheet.role_hint || "Unknown"}</p>
          <p>Last seen: {sheet.last_seen_scene_name || sheet.last_seen_scene_id || "Unknown"}</p>
        </article>
      </section>
    );
  }

  return (
    <section className="drawer-panel drawer-grid">
      <article className="drawer-card">
        <strong>{sheet.name}</strong>
        <p>{sheet.race || "Unknown race"}</p>
        <p>{sheet.status || "No status summary"}</p>
      </article>
      <article className="drawer-card">
        <strong>Signals</strong>
        <p>Mentions: {sheet.mention_count ?? 0}</p>
        <p>Relevance: {sheet.relevance_score ?? 0}</p>
        <p>Tags: {(sheet.tags ?? []).join(", ") || "None"}</p>
      </article>
    </section>
  );
}

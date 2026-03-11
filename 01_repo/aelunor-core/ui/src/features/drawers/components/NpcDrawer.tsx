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
          <strong>Ziel</strong>
          <p>{sheet.goal || "Kein primäres Ziel erfasst."}</p>
        </article>
        <article className="drawer-card">
          <strong>Hintergrund</strong>
          <p>{sheet.backstory_short || "Noch keine kurze Hintergrundbeschreibung verfügbar."}</p>
        </article>
      </section>
    );
  }

  if (active_tab === "attributes") {
    return (
      <section className="drawer-panel">
        <article className="drawer-card">
          <strong>Historie</strong>
          {(sheet.history_notes ?? []).length > 0 ? (
            <ul className="rail-list">
              {sheet.history_notes?.map((entry) => (
                <li key={entry} className="rail-list-item">
                  {entry}
                </li>
              ))}
            </ul>
          ) : (
            <p className="status-muted">Noch keine Historien-Notizen vorhanden.</p>
          )}
        </article>
      </section>
    );
  }

  if (active_tab === "skills") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Verbindungen</strong>
          <p>Fraktion: {sheet.faction || "Keine"}</p>
          <p>Rollenhinweis: {sheet.role_hint || "Unbekannt"}</p>
          <p>Zuletzt gesehen: {sheet.last_seen_scene_name || sheet.last_seen_scene_id || "Unbekannt"}</p>
        </article>
      </section>
    );
  }

  return (
    <section className="drawer-panel drawer-grid">
      <article className="drawer-card">
        <strong>{sheet.name}</strong>
        <p>{sheet.race || "Unbekannte Rasse"}</p>
        <p>{sheet.status || "Keine Statuszusammenfassung"}</p>
      </article>
      <article className="drawer-card">
        <strong>Signale</strong>
        <p>Erwähnungen: {sheet.mention_count ?? 0}</p>
        <p>Relevanz: {sheet.relevance_score ?? 0}</p>
        <p>Tags: {(sheet.tags ?? []).join(", ") || "Keine"}</p>
      </article>
    </section>
  );
}

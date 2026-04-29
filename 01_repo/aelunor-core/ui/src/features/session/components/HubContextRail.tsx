import type { SessionLibraryEntry } from "../../../shared/api/contracts";

interface HubContextRailProps {
  session_count: number;
  has_active_session: boolean;
  latest_entry: SessionLibraryEntry | null;
  active_campaign_id: string | null;
  active_join_code: string | null;
}

function formatUpdatedAt(value: string | null | undefined): string {
  if (!value) {
    return "Noch nicht synchronisiert";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function ArcaneStatusWidget({ has_active_session }: { has_active_session: boolean }) {
  return (
    <div className="hub-arcane-widget" aria-label="Canon State">
      <div className="hub-compass" aria-hidden="true">
        <span className="hub-compass-star" />
      </div>
      <div className="hub-arcane-lines">
        <span>Canon State</span>
        <strong>{has_active_session ? "Stable" : "No active session"}</strong>
      </div>
    </div>
  );
}

export function HubContextRail({
  session_count,
  has_active_session,
  latest_entry,
  active_campaign_id,
  active_join_code,
}: HubContextRailProps) {
  return (
    <aside className="hub-context-rail" aria-label="Campaign Kontext">
      <section className="hub-context-panel aelunor-frame-host">
        <span className="aelunor-frame-overlay is-card" aria-hidden="true" />
        <div className="hub-context-head">
          <span>Campaign Status</span>
          <strong>{has_active_session ? "Session Active" : "Standby"}</strong>
        </div>
        <div className="hub-context-stat">
          <span>Saved Sessions</span>
          <strong>{session_count}</strong>
        </div>
        <div className="hub-context-stat">
          <span>Join Code</span>
          <strong>{active_join_code || latest_entry?.join_code || "n/a"}</strong>
        </div>
      </section>

      <section className="hub-context-panel aelunor-frame-host">
        <span className="aelunor-frame-overlay is-card" aria-hidden="true" />
        <div className="hub-context-head">
          <span>Current Chronicle</span>
          <strong>{latest_entry?.campaign_title ?? latest_entry?.label ?? "Noch keine Chronik"}</strong>
        </div>
        <p className="status-muted">
          {latest_entry
            ? `Zuletzt lokal aktualisiert: ${formatUpdatedAt(latest_entry.updated_at)}`
            : "Erstelle oder join eine Kampagne, um die Chronik zu starten."}
        </p>
        <div className="hub-mini-map" aria-hidden="true" />
      </section>

      <section className="hub-context-panel aelunor-frame-host">
        <span className="aelunor-frame-overlay is-card" aria-hidden="true" />
        <div className="hub-context-head">
          <span>Active Objective</span>
          <strong>{active_campaign_id ? "Campaign State laden" : "Erste Kampagne erstellen"}</strong>
        </div>
        <p className="status-muted">
          {has_active_session
            ? "Lokale Zugangsdaten sind vorhanden. Fortsetzen prüft den Server-State vor dem Einstieg."
            : "Der Hub wartet auf eine neue Host- oder Join-Aktion."}
        </p>
      </section>

      <section className="hub-context-panel aelunor-frame-host">
        <span className="aelunor-frame-overlay is-card" aria-hidden="true" />
        <ArcaneStatusWidget has_active_session={has_active_session} />
      </section>
    </aside>
  );
}

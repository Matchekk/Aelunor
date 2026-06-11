import type { SessionLibraryEntry } from "../../../shared/api/contracts";
import { AelunorPanelFrame } from "../../../shared/ui/aelunorAssets";

interface HubContextRailProps {
  session_count: number;
  has_active_session: boolean;
  latest_entry: SessionLibraryEntry | null;
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

export function HubContextRail({
  session_count,
  has_active_session,
  latest_entry,
  active_join_code,
}: HubContextRailProps) {
  if (!has_active_session && session_count === 0) {
    return (
      <aside className="hub-context-rail is-empty" aria-label="Nächster Schritt">
        <AelunorPanelFrame className="hub-context-panel hub-next-step-panel" variant="compact">
          <div className="hub-context-head">
            <span>Nächster Schritt</span>
            <strong>Vom leeren Hub zum ersten Turn</strong>
          </div>
          <ol className="hub-next-steps">
            <li>Kampagne erstellen</li>
            <li>Party einrichten</li>
            <li>Ersten Story-Turn starten</li>
          </ol>
        </AelunorPanelFrame>
      </aside>
    );
  }

  return (
    <aside className="hub-context-rail" aria-label="Kampagnenkontext">
      <AelunorPanelFrame className="hub-context-panel" variant="compact">
        <div className="hub-context-head">
          <span>{has_active_session ? "Spieler online" : "Gespeicherte Sessions"}</span>
          <strong>{has_active_session ? "Lokale Session bereit" : `${session_count} Chronik${session_count === 1 ? "" : "en"}`}</strong>
        </div>
        {active_join_code || latest_entry?.join_code ? (
          <div className="hub-context-stat">
            <span>Beitrittscode</span>
            <strong>{active_join_code || latest_entry?.join_code}</strong>
          </div>
        ) : null}
      </AelunorPanelFrame>

      <AelunorPanelFrame className="hub-context-panel" variant="compact">
        <div className="hub-context-head">
          <span>{has_active_session ? "Aktuelles Ziel" : "Letzte Chronik"}</span>
          <strong>{has_active_session ? "Nächsten Story-Turn starten" : latest_entry?.campaign_title ?? latest_entry?.label}</strong>
        </div>
        <p className="status-muted">
          {latest_entry
            ? `Zuletzt lokal aktualisiert: ${formatUpdatedAt(latest_entry.updated_at)}`
            : "Wähle eine gespeicherte Session und validiere den Server-State."}
        </p>
      </AelunorPanelFrame>

      {has_active_session ? (
        <AelunorPanelFrame className="hub-context-panel" variant="compact">
          <div className="hub-context-head">
            <span>Canon-Status</span>
            <strong>Bereit zur Prüfung</strong>
          </div>
          <p className="status-muted">
            Fortsetzen lädt Campaign-State, Claims und Canon vor dem Einstieg neu.
          </p>
        </AelunorPanelFrame>
      ) : null}
    </aside>
  );
}

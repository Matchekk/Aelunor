import type { SessionLibraryEntry } from "../../../shared/api/contracts";
import { SessionLibraryItem } from "./SessionLibraryItem";

interface SessionLibraryPanelProps {
  entries: SessionLibraryEntry[];
  resume_pending_campaign_id: string | null;
  on_resume: (entry: SessionLibraryEntry) => void;
  on_edit: (entry: SessionLibraryEntry) => void;
  on_forget: (campaign_id: string) => void;
}

export function SessionLibraryPanel(props: SessionLibraryPanelProps) {
  return (
    <section className="v1-panel session-library-panel hub-campaigns-panel aelunor-frame-host">
      <span className="aelunor-frame-overlay is-card" aria-hidden="true" />
      <div className="v1-panel-head">
        <h2>Meine Kampagnen</h2>
        <span>{props.entries.length} gespeichert</span>
      </div>
      <span className="aelunor-divider is-small" aria-hidden="true" />
      <p className="status-muted">Fortsetzen ist die Standardaktion. Bearbeiten/Entfernen bleiben sekundär.</p>
      <div className="session-library-body">
        {props.entries.length === 0 ? (
          <div className="session-empty aelunor-empty-state">
            Noch keine gespeicherten Sessions. Erstelle eine Kampagne oder tritt einem Raum bei.
          </div>
        ) : (
          props.entries.map((entry) => (
            <SessionLibraryItem
              key={entry.campaign_id}
              entry={entry}
              resume_pending={props.resume_pending_campaign_id === entry.campaign_id}
              on_resume={props.on_resume}
              on_edit={props.on_edit}
              on_forget={props.on_forget}
            />
          ))
        )}
      </div>
    </section>
  );
}

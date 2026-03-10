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
    <section className="v1-panel session-library-panel">
      <details open>
        <summary>
          Session Library <span className="status-muted">({props.entries.length})</span>
        </summary>
        <div className="session-library-body">
          {props.entries.length === 0 ? (
            <div className="session-empty">
              No local sessions saved yet. Create or join one to add it automatically.
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
      </details>
    </section>
  );
}

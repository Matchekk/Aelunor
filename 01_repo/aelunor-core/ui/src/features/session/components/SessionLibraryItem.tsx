import type { SessionLibraryEntry } from "../../../shared/api/contracts";
import { deriveSessionSubtitle } from "../selectors";

interface SessionLibraryItemProps {
  entry: SessionLibraryEntry;
  resume_pending: boolean;
  on_resume: (entry: SessionLibraryEntry) => void;
  on_edit: (entry: SessionLibraryEntry) => void;
  on_forget: (campaign_id: string) => void;
}

export function SessionLibraryItem({ entry, resume_pending, on_resume, on_edit, on_forget }: SessionLibraryItemProps) {
  return (
    <article className="session-library-item hub-campaign-item">
      <div>
        <h3>{entry.label}</h3>
        <p className="status-muted">{deriveSessionSubtitle(entry)}</p>
      </div>
      <div className="session-library-item-actions">
        <button type="button" className="hub-primary-cta" onClick={() => on_resume(entry)} disabled={resume_pending}>
          {resume_pending ? "Resuming..." : "Resume"}
        </button>
        <button type="button" onClick={() => on_edit(entry)}>
          Edit
        </button>
        <button type="button" onClick={() => on_forget(entry.campaign_id)}>
          Forget
        </button>
      </div>
    </article>
  );
}

import { useEffect, useState } from "react";

import type { AuthorsNoteBoard } from "../../../shared/api/contracts";
import { formatBoardTimestamp } from "../selectors";

interface AuthorsNotePanelProps {
  board: AuthorsNoteBoard;
  can_edit: boolean;
  pending: boolean;
  error_message: string | null;
  on_save: (content: string) => void;
}

export function AuthorsNotePanel({ board, can_edit, pending, error_message, on_save }: AuthorsNotePanelProps) {
  const [content, setContent] = useState(board.content);

  useEffect(() => {
    setContent(board.content);
  }, [board.content]);

  return (
    <section className="boards-panel">
      <div className="v1-panel-head">
        <h2>Author&apos;s Note</h2>
        <span>{can_edit ? "Host editable" : "Read-only"}</span>
      </div>
      <p className="status-muted">This note is passed into every turn prompt as direct authorial guidance.</p>
      <label>
        Guidance
        <textarea value={content} readOnly={!can_edit} onChange={(event) => setContent(event.target.value)} />
      </label>
      <div className="status-muted">Updated {formatBoardTimestamp(board.updated_at)}</div>
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
      {can_edit ? (
        <div className="session-inline-actions">
          <button type="button" onClick={() => on_save(content)} disabled={pending}>
            {pending ? "Saving..." : "Save author’s note"}
          </button>
        </div>
      ) : null}
    </section>
  );
}

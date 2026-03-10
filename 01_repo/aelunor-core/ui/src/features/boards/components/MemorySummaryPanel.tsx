import type { MemorySummaryBoard } from "../../../shared/api/contracts";
import { formatBoardTimestamp } from "../selectors";

interface MemorySummaryPanelProps {
  board: MemorySummaryBoard;
}

export function MemorySummaryPanel({ board }: MemorySummaryPanelProps) {
  return (
    <section className="boards-panel">
      <div className="v1-panel-head">
        <h2>Memory Summary</h2>
        <span>Read-only</span>
      </div>
      <p className="status-muted">This summary is rebuilt from the story timeline by the backend.</p>
      <article className="boards-memory-block">
        <p>{board.content || "No memory summary is available yet."}</p>
      </article>
      <div className="status-muted">
        Updated through turn {board.updated_through_turn} • {formatBoardTimestamp(board.updated_at)}
      </div>
    </section>
  );
}

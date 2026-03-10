import type { SetupProgressPayload, SetupReadyCounter } from "../../../shared/api/contracts";

interface SetupProgressProps {
  chapter_label: string;
  chapter_index: number;
  chapter_total: number;
  chapter_progress: SetupProgressPayload | null;
  global_progress: SetupProgressPayload | null;
  ready_counter: SetupReadyCounter;
}

function percent(progress: SetupProgressPayload | null): number {
  if (!progress || progress.total <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round((progress.answered / progress.total) * 100)));
}

function summary(progress: SetupProgressPayload | null, fallback: string): string {
  if (!progress || progress.total <= 0) {
    return fallback;
  }
  return `${progress.answered}/${progress.total}`;
}

export function SetupProgress({
  chapter_label,
  chapter_index,
  chapter_total,
  chapter_progress,
  global_progress,
  ready_counter,
}: SetupProgressProps) {
  return (
    <section className="v1-panel setup-progress-panel">
      <div className="v1-panel-head">
        <h2>Progress</h2>
        <span>{summary(global_progress, "No totals yet")}</span>
      </div>
      <div className="setup-progress-grid">
        <div className="setup-progress-row">
          <div className="setup-progress-copy">
            <strong>{chapter_label}</strong>
            <span className="status-muted">
              Chapter {chapter_index}/{chapter_total} • {summary(chapter_progress, "No chapter totals")}
            </span>
          </div>
          <div className="setup-progress-track">
            <div className="setup-progress-fill" style={{ width: `${percent(chapter_progress)}%` }} />
          </div>
        </div>
        <div className="setup-progress-row">
          <div className="setup-progress-copy">
            <strong>Global</strong>
            <span className="status-muted">{summary(global_progress, "No global totals")}</span>
          </div>
          <div className="setup-progress-track">
            <div className="setup-progress-fill is-global" style={{ width: `${percent(global_progress)}%` }} />
          </div>
        </div>
        <div className="setup-progress-ready">
          <span className="status-pill">
            Ready {ready_counter.ready}/{ready_counter.total}
          </span>
        </div>
      </div>
    </section>
  );
}

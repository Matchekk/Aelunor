import type { SetupRandomResponse } from "../../../shared/api/contracts";

interface RandomSuggestionPanelProps {
  open: boolean;
  preview: SetupRandomResponse | null;
  mode: "single" | "all";
  loading: boolean;
  apply_pending: boolean;
  disabled: boolean;
  on_mode_change: (mode: "single" | "all") => void;
  on_refresh: () => void;
  on_apply: () => void;
  on_close: () => void;
}

export function RandomSuggestionPanel({
  open,
  preview,
  mode,
  loading,
  apply_pending,
  disabled,
  on_mode_change,
  on_refresh,
  on_apply,
  on_close,
}: RandomSuggestionPanelProps) {
  if (!open) {
    return null;
  }

  return (
    <section className="v1-panel setup-random-panel">
      <div className="v1-panel-head">
        <h2>Random Suggestions</h2>
        <button type="button" onClick={on_close} disabled={loading || apply_pending}>
          Close
        </button>
      </div>
      <div className="setup-random-modes">
        <label>
          <input
            type="radio"
            checked={mode === "single"}
            disabled={loading || apply_pending}
            onChange={() => on_mode_change("single")}
          />
          Current question
        </label>
        <label>
          <input
            type="radio"
            checked={mode === "all"}
            disabled={loading || apply_pending}
            onChange={() => on_mode_change("all")}
          />
          Remaining chapter
        </label>
      </div>
      {preview?.preview_answers.length ? (
        <div className="setup-random-list">
          {preview.preview_answers.map((entry) => (
            <article key={`${entry.question_id}-${entry.preview_text}`} className="setup-random-item">
              <strong>{entry.label || entry.question_id}</strong>
              <p>{entry.preview_text || "No preview text returned."}</p>
            </article>
          ))}
        </div>
      ) : (
        <div className="setup-empty-state">No random preview is loaded yet.</div>
      )}
      <div className="setup-inline-actions">
        <button type="button" onClick={on_refresh} disabled={disabled || loading || apply_pending}>
          {loading ? "Generating..." : "Refresh preview"}
        </button>
        <button
          type="button"
          onClick={on_apply}
          disabled={disabled || apply_pending || !preview || preview.preview_answers.length === 0}
        >
          {apply_pending ? "Applying..." : "Apply suggestion"}
        </button>
      </div>
    </section>
  );
}

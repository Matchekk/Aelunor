interface ReviewPanelProps {
  mode: "world" | "character";
  entries: Array<{ label: string; value: string }>;
}

export function ReviewPanel({ mode, entries }: ReviewPanelProps) {
  return (
    <section className="setup-review-panel">
      <div className="v1-panel-head">
        <h2>{mode === "world" ? "World Review" : "Character Review"}</h2>
        <span>Final check</span>
      </div>
      <p className="status-muted">
        Confirm the current setup summary before the last answer is committed to the backend.
      </p>
      <div className="setup-review-grid">
        {entries.length > 0 ? (
          entries.map((entry) => (
            <article key={entry.label} className="setup-review-item">
              <strong>{entry.label}</strong>
              <p>{entry.value}</p>
            </article>
          ))
        ) : (
          <article className="setup-review-item">
            <p>No review summary is available for this step yet.</p>
          </article>
        )}
      </div>
    </section>
  );
}

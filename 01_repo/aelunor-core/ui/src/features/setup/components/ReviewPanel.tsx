interface ReviewPanelProps {
  mode: "world" | "character";
  entries: Array<{ label: string; value: string }>;
}

export function ReviewPanel({ mode, entries }: ReviewPanelProps) {
  return (
    <section className="setup-review-panel">
      <div className="v1-panel-head">
        <h2>{mode === "world" ? "Welt-Überprüfung" : "Charakter-Überprüfung"}</h2>
        <span>Letzte Kontrolle</span>
      </div>
      <p className="status-muted">
        Prüfe die Zusammenfassung, bevor die letzte Antwort endgültig gespeichert wird.
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
            <p>Für diesen Schritt liegt noch keine Zusammenfassung vor.</p>
          </article>
        )}
      </div>
    </section>
  );
}

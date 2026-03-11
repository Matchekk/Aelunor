interface PrePlayComposerHintProps {
  phase_display: string;
}

export function PrePlayComposerHint({ phase_display }: PrePlayComposerHintProps) {
  return (
    <section className="composer-standby hud-surface panel">
      <div className="v1-panel-head composer-dock-head">
        <h2>Zug-Eingabe</h2>
        <span>{phase_display}</span>
      </div>
      <p className="status-muted">
        Der Composer bleibt bis zur aktiven Spielphase gesperrt. Du kannst in dieser Zeit den Verlauf lesen und die
        Metadaten in den Boards prüfen.
      </p>
    </section>
  );
}


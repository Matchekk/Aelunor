const FEATURES = [
  {
    label: "Story-first",
    text: "Kampagnen, Figuren und Weltzustand bleiben im Fokus.",
  },
  {
    label: "Live Table",
    text: "Presence, Claims und Sessionwechsel sind direkt erreichbar.",
  },
  {
    label: "Canon Ready",
    text: "Boards, Timeline und Setup führen zur spielbaren Szene.",
  },
];

export function HubFeatureCards() {
  return (
    <section className="hub-feature-grid" aria-label="Aelunor Überblick">
      {FEATURES.map((feature) => (
        <article key={feature.label} className="hub-feature-card aelunor-frame-host">
          <span className="aelunor-frame-overlay is-card" aria-hidden="true" />
          <span>{feature.label}</span>
          <span className="aelunor-divider is-small" aria-hidden="true" />
          <strong>{feature.text}</strong>
        </article>
      ))}
    </section>
  );
}

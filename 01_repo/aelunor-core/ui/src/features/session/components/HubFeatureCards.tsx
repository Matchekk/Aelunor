import { AelunorDivider, AelunorPanelFrame } from "../../../shared/ui/aelunorAssets";

const FEATURES = [
  {
    label: "Story im Fokus",
    text: "Kampagnen, Figuren und Weltzustand bleiben im Fokus.",
  },
  {
    label: "Live-Tisch",
    text: "Spielerpräsenz, Claims und Sessionwechsel sind direkt erreichbar.",
  },
  {
    label: "Canon bereit",
    text: "Boards, Timeline und Setup führen zur spielbaren Szene.",
  },
];

export function HubFeatureCards() {
  return (
    <section className="hub-feature-grid" aria-label="Aelunor Überblick">
      {FEATURES.map((feature) => (
        <AelunorPanelFrame key={feature.label} as="article" className="hub-feature-card" variant="compact">
          <span>{feature.label}</span>
          <AelunorDivider variant="small" />
          <strong>{feature.text}</strong>
        </AelunorPanelFrame>
      ))}
    </section>
  );
}

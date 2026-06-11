import type { ReactNode } from "react";

import type { V1AppPage } from "../../../app/routing/routes";
import { AelunorDivider, AelunorPanelFrame } from "../../../shared/ui/aelunorAssets";

interface HubAppPageProps {
  page: V1AppPage;
  has_active_session: boolean;
  hero: ReactNode;
  features: ReactNode;
  continuation: ReactNode;
  session_library: ReactNode;
  create_campaign: ReactNode;
  join_campaign: ReactNode;
  context_rail: ReactNode;
  diagnostics: ReactNode;
  on_open_campaigns: () => void;
  on_open_campaign_surface: (page: V1AppPage) => void;
}

interface DomainPageCopy {
  eyebrow: string;
  title: string;
  description: string;
  active_detail: string;
  standby_detail: string;
  primary_label: string;
}

const DOMAIN_PAGE_COPY: Record<Exclude<V1AppPage, "hub" | "campaigns">, DomainPageCopy> = {
  characters: {
    eyebrow: "Party & Claims",
    title: "Figuren",
    description: "Charaktere, Claims, Sheets und Setup-Fortschritt bekommen hier ihren eigenen Arbeitsbereich.",
    active_detail: "Eine aktive lokale Session ist vorhanden. Öffne die Kampagne, um Charaktere und Claims im Live-Zustand zu bearbeiten.",
    standby_detail: "Starte zuerst eine Kampagne oder tritt einer Runde bei, damit Charakterdaten an echte Kampagnen-Flows gebunden bleiben.",
    primary_label: "Charaktere öffnen",
  },
  world: {
    eyebrow: "Weltbibel",
    title: "Welt",
    description: "Orte, Fraktionen, Weltwissen und Canon-Regeln werden aus dem Kampagnenzustand heraus gepflegt.",
    active_detail: "Öffne die Kampagnenansicht mit dem Weltwissen-Board, um am aktuellen Weltzustand zu arbeiten.",
    standby_detail: "Ohne aktive Kampagne gibt es noch keinen reload-sicheren Weltzustand.",
    primary_label: "Welt-Board öffnen",
  },
  quests: {
    eyebrow: "Plot & Ziele",
    title: "Quests",
    description: "Story-Karten, offene Ziele und Plotpunkte werden als eigener Navigationsbereich geführt.",
    active_detail: "Öffne die Kampagne direkt mit Story-Karten, um aktuelle Ziele und Plotpunkte zu sehen.",
    standby_detail: "Quests entstehen aus Kampagnen-Turns und brauchen deshalb zuerst eine aktive Chronik.",
    primary_label: "Story-Karten öffnen",
  },
  inventory: {
    eyebrow: "Ausrüstung & Ressourcen",
    title: "Inventar",
    description: "Ausrüstung, Items und Ressourcen werden künftig aus dem Kampagnenzustand heraus fokussiert erreichbar.",
    active_detail: "Die aktive Kampagne ist verfügbar. Öffne den Spieltisch, um Inventar-Zustand an echter Spiellogik zu prüfen.",
    standby_detail: "Inventar ohne aktive Kampagne wäre nur Platzhalterzustand; erstelle zuerst eine Session oder tritt einer Runde bei.",
    primary_label: "Kampagne öffnen",
  },
  codex: {
    eyebrow: "Canon & Lore",
    title: "Kodex",
    description: "Entdeckte Lore, Völker, Kreaturentypen und Canon-Einträge bekommen hier eine eigene Einstiegsfläche.",
    active_detail: "Öffne die Kampagnen-Kontextsuche, um Kodex- und Canon-Informationen im aktuellen Zustand zu nutzen.",
    standby_detail: "Kodex-Inhalte müssen aus einer Kampagne kommen, damit sie nicht parallel zur Persistenz laufen.",
    primary_label: "Kodex-Kontext öffnen",
  },
};

function HubPageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <AelunorPanelFrame className="v1-panel hub-page-header" variant="hero" texture>
      <p className="hub-hero-chapter">{eyebrow}</p>
      <AelunorDivider variant="small" />
      <h1>{title}</h1>
      <p className="hub-page-description">{description}</p>
    </AelunorPanelFrame>
  );
}

function DomainPage({
  page,
  has_active_session,
  on_open_campaigns,
  on_open_campaign_surface,
}: Pick<HubAppPageProps, "page" | "has_active_session" | "on_open_campaigns" | "on_open_campaign_surface">) {
  if (page === "hub" || page === "campaigns") {
    return null;
  }

  const copy = DOMAIN_PAGE_COPY[page];

  return (
    <>
      <HubPageHeader eyebrow={copy.eyebrow} title={copy.title} description={copy.description} />
      <section className="hub-dashboard-grid is-single-column">
        <div className="hub-dashboard-main">
          <AelunorPanelFrame className="v1-panel hub-domain-panel" variant="card" texture>
            <div className="v1-panel-head">
              <h2>{has_active_session ? "Kampagnenansicht bereit" : "Kampagne erforderlich"}</h2>
              <span>{copy.eyebrow}</span>
            </div>
            <AelunorDivider variant="small" />
            <p className="status-muted">{has_active_session ? copy.active_detail : copy.standby_detail}</p>
            <div className="hub-domain-actions">
              {has_active_session ? (
                <button type="button" className="hub-primary-cta aelunor-button-ornate" onClick={() => on_open_campaign_surface(page)}>
                  {copy.primary_label}
                </button>
              ) : (
                <button type="button" className="hub-primary-cta aelunor-button-ornate" onClick={on_open_campaigns}>
                  Kampagne starten oder beitreten
                </button>
              )}
            </div>
          </AelunorPanelFrame>
        </div>
      </section>
    </>
  );
}

export function HubAppPage({
  page,
  has_active_session,
  hero,
  features,
  continuation,
  session_library,
  create_campaign,
  join_campaign,
  context_rail,
  diagnostics,
  on_open_campaigns,
  on_open_campaign_surface,
}: HubAppPageProps) {
  if (page === "hub") {
    return (
      <>
        {hero}
        <section className="hub-overview-grid" aria-label="Hub Übersicht">
          <div className="hub-overview-main">
            {has_active_session ? features : null}
            {continuation}
          </div>
          {context_rail}
        </section>
      </>
    );
  }

  if (page === "campaigns") {
    return (
      <>
        <HubPageHeader
          eyebrow="Kampagnensteuerung"
          title="Kampagnen"
          description="Gespeicherte Sessions, neue Runden und Join-Flows sind jetzt aus dem Hub herausgezogen."
        />
        <section className="hub-dashboard-grid is-single-column">
          <div className="hub-dashboard-main">
            {continuation}
            <section className="hub-campaigns-main">{session_library}</section>
          </div>
          <section className="hub-actions-grid" aria-label="Kampagnenaktionen">
            <div id="hub-create-panel">{create_campaign}</div>
            <div id="hub-join-panel">{join_campaign}</div>
          </section>
        </section>
        {diagnostics}
      </>
    );
  }

  return (
    <DomainPage
      page={page}
      has_active_session={has_active_session}
      on_open_campaigns={on_open_campaigns}
      on_open_campaign_surface={on_open_campaign_surface}
    />
  );
}

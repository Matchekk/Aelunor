import type { CodexDrawerPayload } from "../selectors";
import { ScopeLabel } from "../../scenes/components/ScopeLabel";
import { partyScopeLabel } from "../../scenes/scopeLabels";

interface CodexDrawerProps {
  payload: CodexDrawerPayload;
  active_tab: string;
}

function text(value: unknown, fallback = "-"): string {
  const normalized = typeof value === "string" ? value.trim() : "";
  return normalized || fallback;
}

function list(value: unknown): string {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string" && entry.length > 0).join(", ") : "";
}

export function CodexDrawer({ payload, active_tab }: CodexDrawerProps) {
  const { kind, profile, entry } = payload;

  if (active_tab === "class") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Identität</strong>
          <p>{text(profile.description_short || profile.category)}</p>
          <p>{text(profile.appearance)}</p>
        </article>
      </section>
    );
  }

  if (active_tab === "attributes") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Herkunft</strong>
          <p>{text(profile.homeland || profile.habitat)}</p>
          <p>{text(profile.culture || profile.behavior)}</p>
        </article>
      </section>
    );
  }

  if (active_tab === "skills") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Merkmale</strong>
          <p>Stärken: {list(profile.strength_tags) || "Keine"}</p>
          <p>Schwächen: {list(profile.weakness_tags) || "Keine"}</p>
          {kind === "race" ? <p>Klassenaffinitäten: {list(profile.class_affinities) || "Keine"}</p> : null}
        </article>
      </section>
    );
  }

  if (active_tab === "injuries") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Fähigkeiten</strong>
          <p>{kind === "race" ? `Bekannte Individuen: ${list(entry.known_individuals) || "Keine"}` : `Beobachtet: ${list(entry.observed_abilities) || "Keine"}`}</p>
        </article>
      </section>
    );
  }

  if (active_tab === "gear") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Wissen</strong>
          <p>{list(entry.known_facts) || text(profile.lore_notes || profile.notable_traits)}</p>
        </article>
      </section>
    );
  }

  return (
    <section className="drawer-panel drawer-grid">
      <article className="drawer-card">
        <strong>{payload.name}</strong>
        <p>{kind === "race" ? "Rassen-" : "Bestien-"}Codexeintrag</p>
        <p>Wissensstufe {payload.knowledge_level}/4</p>
        <div className="composer-status-pills">
          <ScopeLabel scope={partyScopeLabel()} />
        </div>
      </article>
      <article className="drawer-card">
        <strong>Belege</strong>
        <p>Begegnungen: {Number(entry.encounter_count || 0)}</p>
        <p>Bekannte Fakten: {Array.isArray(entry.known_facts) ? entry.known_facts.length : 0}</p>
      </article>
    </section>
  );
}

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
          <strong>Identity</strong>
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
          <strong>Origin</strong>
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
          <strong>Traits</strong>
          <p>Strengths: {list(profile.strength_tags) || "None"}</p>
          <p>Weaknesses: {list(profile.weakness_tags) || "None"}</p>
          {kind === "race" ? <p>Class affinities: {list(profile.class_affinities) || "None"}</p> : null}
        </article>
      </section>
    );
  }

  if (active_tab === "injuries") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Abilities</strong>
          <p>{kind === "race" ? `Known individuals: ${list(entry.known_individuals) || "None"}` : `Observed: ${list(entry.observed_abilities) || "None"}`}</p>
        </article>
      </section>
    );
  }

  if (active_tab === "gear") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Lore</strong>
          <p>{list(entry.known_facts) || text(profile.lore_notes || profile.notable_traits)}</p>
        </article>
      </section>
    );
  }

  return (
    <section className="drawer-panel drawer-grid">
      <article className="drawer-card">
        <strong>{payload.name}</strong>
        <p>{kind === "race" ? "Race" : "Beast"} codex entry</p>
        <p>Knowledge level {payload.knowledge_level}/4</p>
        <div className="composer-status-pills">
          <ScopeLabel scope={partyScopeLabel()} />
        </div>
      </article>
      <article className="drawer-card">
        <strong>Evidence</strong>
        <p>Encounters: {Number(entry.encounter_count || 0)}</p>
        <p>Known facts: {Array.isArray(entry.known_facts) ? entry.known_facts.length : 0}</p>
      </article>
    </section>
  );
}

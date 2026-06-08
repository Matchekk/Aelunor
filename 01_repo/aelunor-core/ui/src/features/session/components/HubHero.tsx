import type { SessionLibraryEntry } from "../../../shared/api/contracts";
import { AelunorDivider, AelunorPanelFrame } from "../../../shared/ui/aelunorAssets";

interface HubHeroProps {
  has_active_session: boolean;
  has_saved_sessions: boolean;
  active_campaign_id: string | null;
  latest_entry: SessionLibraryEntry | null;
  resume_pending_campaign_id: string | null;
  on_resume_current: () => void;
  on_resume_latest: () => void;
}

function getHeroTitle(hasActiveSession: boolean, latestEntry: SessionLibraryEntry | null): string {
  if (hasActiveSession) {
    return latestEntry?.campaign_title ?? latestEntry?.label ?? "Active Campaign";
  }
  if (latestEntry) {
    return latestEntry.campaign_title ?? latestEntry.label;
  }
  return "Starte deine erste Chronik";
}

export function HubHero({
  has_active_session,
  has_saved_sessions,
  active_campaign_id,
  latest_entry,
  resume_pending_campaign_id,
  on_resume_current,
  on_resume_latest,
}: HubHeroProps) {
  const canResumeCurrent = has_active_session && Boolean(active_campaign_id);
  const canResumeLatest = !canResumeCurrent && Boolean(latest_entry);
  const activePending = active_campaign_id ? resume_pending_campaign_id === active_campaign_id : false;
  const latestPending = latest_entry ? resume_pending_campaign_id === latest_entry.campaign_id : false;
  const heroTitle = getHeroTitle(has_active_session, latest_entry);

  return (
    <AelunorPanelFrame className="hub-hero-panel" variant="hero" texture aria-labelledby="hub-hero-title">
      <div className="hub-hero-copy">
        <p className="hub-hero-chapter">Campaign Control</p>
        <AelunorDivider variant="small" />
        <h1 id="hub-hero-title">{heroTitle}</h1>
        <p className="hub-hero-subtitle">
          {has_active_session
            ? "Eine lokale Session ist bereit. Öffne den Spieltisch und setze die Chronik fort."
            : has_saved_sessions
              ? "Setze deine letzte Chronik fort, starte eine neue Kampagne oder tritt per Code bei."
              : "Erstelle eine Kampagne, tritt per Code bei oder öffne eine Demo-Chronik zum Testen."}
        </p>
        <p className="hub-hero-description">
          {has_active_session || has_saved_sessions
            ? "Der Hub bündelt gespeicherte Sessions und den Einstieg in den nächsten Story-Turn."
            : "Danach erscheinen hier deine gespeicherten Chroniken und direkten Fortsetzen-Aktionen."}
        </p>
        <div className="hub-hero-actions">
          {canResumeCurrent ? (
            <button type="button" className="hub-hero-primary aelunor-button-ornate" onClick={on_resume_current} disabled={activePending}>
              {activePending ? "Session wird geprüft" : "Zum Spieltisch"}
            </button>
          ) : canResumeLatest ? (
            <button type="button" className="hub-hero-primary aelunor-button-ornate" onClick={on_resume_latest} disabled={latestPending}>
              {latestPending ? "Session wird geprüft" : "Weiter spielen"}
            </button>
          ) : (
            <a className="hub-hero-primary aelunor-button-ornate" href="/v1/campaigns#hub-create-panel">
              Neue Kampagne erstellen
            </a>
          )}
          <a className="hub-hero-secondary aelunor-button-ornate is-secondary" href="/v1/campaigns#hub-join-panel">
            Per Code beitreten
          </a>
        </div>
      </div>
    </AelunorPanelFrame>
  );
}

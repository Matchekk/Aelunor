import type { SessionLibraryEntry } from "../../../shared/api/contracts";
import { AelunorDivider, AelunorPanelFrame } from "../../../shared/ui/aelunorAssets";

interface HubHeroProps {
  has_active_session: boolean;
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
  return latestEntry?.campaign_title ?? latestEntry?.label ?? "Campaign Hub";
}

export function HubHero({
  has_active_session,
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
        <p className="hub-hero-subtitle">Öffne deine laufende Chronik, gründe eine neue Runde oder tritt per Code an den Spieltisch.</p>
        <p className="hub-hero-description">
          Der Hub bündelt gespeicherte Sessions, lokale Claims und den Einstieg in den nächsten Story-Turn.
        </p>
        <div className="hub-hero-actions">
          {canResumeCurrent ? (
            <button type="button" className="hub-hero-primary aelunor-button-ornate" onClick={on_resume_current} disabled={activePending}>
              {activePending ? "Session wird geprüft" : "Continue Campaign"}
            </button>
          ) : canResumeLatest ? (
            <button type="button" className="hub-hero-primary aelunor-button-ornate" onClick={on_resume_latest} disabled={latestPending}>
              {latestPending ? "Session wird geprüft" : "Continue Campaign"}
            </button>
          ) : (
            <a className="hub-hero-primary aelunor-button-ornate" href="/v1/campaigns">
              Create Campaign
            </a>
          )}
          <a className="hub-hero-secondary aelunor-button-ornate is-secondary" href="/v1/campaigns">
            Join Campaign
          </a>
        </div>
      </div>
    </AelunorPanelFrame>
  );
}

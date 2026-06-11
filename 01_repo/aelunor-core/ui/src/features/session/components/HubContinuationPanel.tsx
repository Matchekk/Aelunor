import type { SessionLibraryEntry } from "../../../shared/api/contracts";
import { AelunorDivider, AelunorPanelFrame } from "../../../shared/ui/aelunorAssets";
import { ChronicleBookOpeningAnimation } from "../../../shared/ui/ChronicleBookOpeningAnimation";
import { WaitingInline, WaitingSectionOverlay } from "../../../shared/waiting/components";

interface HubContinuationPanelProps {
  has_active_session: boolean;
  active_campaign_id: string | null;
  active_join_code: string | null;
  latest_entry: SessionLibraryEntry | null;
  resume_pending_campaign_id: string | null;
  status_message: string | null;
  resume_error: string | null;
  on_resume_current: () => void;
  on_resume_latest: () => void;
  on_clear_current: () => void;
}

export function HubContinuationPanel({
  has_active_session,
  active_campaign_id,
  active_join_code,
  latest_entry,
  resume_pending_campaign_id,
  status_message,
  resume_error,
  on_resume_current,
  on_resume_latest,
  on_clear_current,
}: HubContinuationPanelProps) {
  const activePending = has_active_session && active_campaign_id ? resume_pending_campaign_id === active_campaign_id : false;
  const latestPending = latest_entry ? resume_pending_campaign_id === latest_entry.campaign_id : false;

  return (
    <AelunorPanelFrame className="v1-panel hub-continuation" variant="card">
      <WaitingSectionOverlay target="hub_resume" />
      <div className="v1-panel-head">
        <h2>{has_active_session ? "Aktive Session" : latest_entry ? "Zuletzt gespielt" : "Noch keine gespeicherten Sessions"}</h2>
        <span>{has_active_session ? "Bereit" : latest_entry ? "Chronik" : "Noch leer"}</span>
      </div>
      <AelunorDivider variant="small" />
      <WaitingInline target="hub_resume" className="hub-waiting-inline" />
      {resume_pending_campaign_id ? (
        <div className="hub-resume-loading">
          <ChronicleBookOpeningAnimation size={96} looping />
        </div>
      ) : null}
      {has_active_session ? (
        <div className="hub-continuation-block">
          <strong>{latest_entry?.campaign_title ?? latest_entry?.label ?? "Aktive lokale Session"}</strong>
          <p className="status-muted">
            {active_join_code ? `Code ${active_join_code}` : "Aktive Sitzung"}
          </p>
          <div className="hub-continuation-actions">
            <button type="button" className="hub-primary-cta aelunor-button-ornate" onClick={on_resume_current} disabled={activePending}>
              {activePending ? "Prüfe Session..." : "Zum Spieltisch"}
            </button>
            <button type="button" className="hub-secondary-cta" onClick={on_resume_current} disabled={activePending}>
              Nächster Story-Turn
            </button>
            <button type="button" className="hub-secondary-cta" onClick={on_clear_current}>
              Session beenden
            </button>
          </div>
        </div>
      ) : latest_entry ? (
        <div className="hub-continuation-block">
          <strong>Zuletzt gespielt: {latest_entry.label}</strong>
          <p className="status-muted">
            {latest_entry.campaign_title ? `${latest_entry.campaign_title} · ` : ""}Code {latest_entry.join_code || "n/a"}
          </p>
          <div className="hub-continuation-actions">
            <button type="button" className="hub-primary-cta aelunor-button-ornate" onClick={on_resume_latest} disabled={latestPending}>
              {latestPending ? "Prüfe Session..." : "Weiter spielen"}
            </button>
            <a className="hub-secondary-cta" href="/v1/campaigns">
              Kampagne verwalten
            </a>
            <a className="hub-secondary-cta" href="/v1/campaigns#hub-create-panel">
              Neue Kampagne
            </a>
          </div>
        </div>
      ) : (
        <div className="hub-continuation-empty aelunor-empty-state">
          <img
            className="hub-empty-chronicle-seal"
            src="/v1/brand/illustrations/empty-chronicle-seal.webp"
            alt=""
            aria-hidden="true"
          />
          <div>
            <strong>Keine gespeicherten Sessions</strong>
            <p>Hier erscheinen deine Chroniken, sobald du eine Kampagne gestartet hast.</p>
          </div>
          <div className="hub-continuation-actions">
            <a className="hub-primary-cta aelunor-button-ornate" href="/v1/campaigns#hub-create-panel">
              Neue Kampagne erstellen
            </a>
            <a className="hub-secondary-cta" href="/v1/campaigns#hub-join-panel">
              Per Code beitreten
            </a>
          </div>
        </div>
      )}
      {status_message ? <div className="session-feedback success">{status_message}</div> : null}
      {resume_error ? <div className="session-feedback error">{resume_error}</div> : null}
    </AelunorPanelFrame>
  );
}

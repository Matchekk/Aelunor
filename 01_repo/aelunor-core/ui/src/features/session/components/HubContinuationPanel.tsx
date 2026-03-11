import type { SessionLibraryEntry } from "../../../shared/api/contracts";
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
    <section className="v1-panel hub-continuation">
      <WaitingSectionOverlay target="hub_resume" />
      <div className="v1-panel-head">
        <h2>Weiter spielen</h2>
        <span>Primäraktion</span>
      </div>
      <WaitingInline target="hub_resume" className="hub-waiting-inline" />
      {has_active_session ? (
        <div className="hub-continuation-block">
          <strong>Aktive lokale Session</strong>
          <p className="status-muted">
            campaign_id: {active_campaign_id}
            {active_join_code ? ` • code ${active_join_code}` : ""}
          </p>
          <div className="hub-continuation-actions">
            <button type="button" className="hub-primary-cta" onClick={on_resume_current} disabled={activePending}>
              {activePending ? "Prüfe Session..." : "Fortsetzen"}
            </button>
            <button type="button" onClick={on_clear_current}>
              Aktive Session löschen
            </button>
          </div>
        </div>
      ) : latest_entry ? (
        <div className="hub-continuation-block">
          <strong>Zuletzt gespielt: {latest_entry.label}</strong>
          <p className="status-muted">
            {latest_entry.campaign_title ? `${latest_entry.campaign_title} • ` : ""}Code {latest_entry.join_code || "n/a"}
          </p>
          <div className="hub-continuation-actions">
            <button type="button" className="hub-primary-cta" onClick={on_resume_latest} disabled={latestPending}>
              {latestPending ? "Prüfe Session..." : "Zuletzt gespielte Session öffnen"}
            </button>
          </div>
        </div>
      ) : (
        <div className="hub-continuation-empty">
          <p>Noch keine gespeicherten Sessions. Starte eine neue Kampagne oder tritt per Code bei.</p>
        </div>
      )}
      {status_message ? <div className="session-feedback success">{status_message}</div> : null}
      {resume_error ? <div className="session-feedback error">{resume_error}</div> : null}
    </section>
  );
}

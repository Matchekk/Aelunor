interface HeroPanelProps {
  has_active_session: boolean;
  active_campaign_id: string | null;
  active_join_code: string | null;
  resume_pending: boolean;
  status_message: string | null;
  resume_error: string | null;
  on_resume_current: () => void;
  on_clear_current: () => void;
}

export function HeroPanel(props: HeroPanelProps) {
  return (
    <section className="v1-panel session-hero">
      <div className="session-hero-kicker">Aelunor UI v1</div>
      <h1>Session Hub</h1>
      <p className="status-muted">
        Create a campaign, join with a code, or resume a saved local session. This is the new v1 entry into Claim,
        Setup, and Play while legacy slash remains untouched.
      </p>
      {props.has_active_session ? (
        <div className="session-hero-active">
          <div>
            <strong>Active local session detected</strong>
            <div className="status-muted">
              campaign_id: {props.active_campaign_id} {props.active_join_code ? `• join_code: ${props.active_join_code}` : ""}
            </div>
          </div>
          <div className="session-hero-actions">
            <button type="button" onClick={props.on_resume_current} disabled={props.resume_pending}>
              {props.resume_pending ? "Checking..." : "Resume current session"}
            </button>
            <button type="button" onClick={props.on_clear_current}>
              Clear local active session
            </button>
          </div>
        </div>
      ) : null}
      {props.status_message ? <div className="session-feedback success">{props.status_message}</div> : null}
      {props.resume_error ? <div className="session-feedback error">{props.resume_error}</div> : null}
    </section>
  );
}

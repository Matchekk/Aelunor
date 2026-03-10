interface ClaimHeaderProps {
  title: string;
  meta_line: string;
  join_code: string | null;
  on_leave_session: () => void;
}

export function ClaimHeader({ title, meta_line, join_code, on_leave_session }: ClaimHeaderProps) {
  return (
    <section className="v1-panel claim-header">
      <div className="claim-header-copy">
        <div className="session-hero-kicker">Campaign Gate</div>
        <h1>{title}</h1>
        <p className="status-muted">{meta_line}</p>
      </div>
      <div className="claim-header-actions">
        {join_code ? <span className="status-pill">Code {join_code}</span> : null}
        <button type="button" onClick={on_leave_session}>
          Leave to Session Hub
        </button>
      </div>
    </section>
  );
}

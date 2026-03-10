interface SetupHeaderProps {
  title: string;
  subtitle: string;
  phase_display: string;
  campaign_title: string;
}

export function SetupHeader({ title, subtitle, phase_display, campaign_title }: SetupHeaderProps) {
  return (
    <header className="setup-header">
      <div className="setup-header-copy">
        <div className="v1-topbar-kicker">Aelunor v1 Setup</div>
        <h1>{title}</h1>
        <p className="status-muted">{subtitle}</p>
      </div>
      <div className="setup-header-meta">
        <span className="status-pill">{phase_display}</span>
        <span className="status-pill">{campaign_title}</span>
      </div>
    </header>
  );
}

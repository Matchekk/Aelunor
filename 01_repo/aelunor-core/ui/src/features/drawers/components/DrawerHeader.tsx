interface DrawerHeaderProps {
  title: string;
  subtitle: string;
  on_close: () => void;
}

export function DrawerHeader({ title, subtitle, on_close }: DrawerHeaderProps) {
  return (
    <header className="drawer-header drawer-head">
      <div>
        <div className="v1-topbar-kicker panelTitle">CHARAKTERBOGEN</div>
        <h2>{title}</h2>
        <p className="status-muted">{subtitle}</p>
      </div>
      <button type="button" onClick={on_close}>
        Schließen
      </button>
    </header>
  );
}

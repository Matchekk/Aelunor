interface DrawerHeaderProps {
  title: string;
  subtitle: string;
  on_close: () => void;
}

export function DrawerHeader({ title, subtitle, on_close }: DrawerHeaderProps) {
  return (
    <header className="drawer-header">
      <div>
        <div className="v1-topbar-kicker">Campaign Drawer</div>
        <h2>{title}</h2>
        <p className="status-muted">{subtitle}</p>
      </div>
      <button type="button" onClick={on_close}>
        Close
      </button>
    </header>
  );
}

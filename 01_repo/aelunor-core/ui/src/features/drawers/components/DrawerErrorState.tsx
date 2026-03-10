interface DrawerErrorStateProps {
  message: string;
  on_retry?: () => void;
  on_close: () => void;
}

export function DrawerErrorState({ message, on_retry, on_close }: DrawerErrorStateProps) {
  return (
    <section className="drawer-state">
      <div className="v1-panel-head">
        <h2>Drawer load failed</h2>
      </div>
      <div className="session-feedback error">{message}</div>
      <div className="session-inline-actions">
        {on_retry ? (
          <button type="button" onClick={on_retry}>
            Retry load
          </button>
        ) : null}
        <button type="button" onClick={on_close}>
          Close drawer
        </button>
      </div>
    </section>
  );
}

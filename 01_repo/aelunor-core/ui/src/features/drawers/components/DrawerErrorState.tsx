interface DrawerErrorStateProps {
  message: string;
  on_retry?: () => void;
  on_close: () => void;
}

export function DrawerErrorState({ message, on_retry, on_close }: DrawerErrorStateProps) {
  return (
    <section className="drawer-state">
      <div className="v1-panel-head">
        <h2>Charakterbogen konnte nicht geladen werden</h2>
      </div>
      <div className="session-feedback error">{message}</div>
      <div className="session-inline-actions">
        {on_retry ? (
          <button type="button" onClick={on_retry}>
            Erneut laden
          </button>
        ) : null}
        <button type="button" onClick={on_close}>
          Schließen
        </button>
      </div>
    </section>
  );
}

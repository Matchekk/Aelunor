import { WaitingInline } from "../../../shared/waiting/components";

export function DrawerLoadingState() {
  return (
    <section className="drawer-state">
      <div className="v1-panel-head">
        <h2>Charakterbogen wird geladen</h2>
      </div>
      <WaitingInline target="drawer" />
      <p className="status-muted">Aktuelle Bogen-Daten werden geladen.</p>
    </section>
  );
}

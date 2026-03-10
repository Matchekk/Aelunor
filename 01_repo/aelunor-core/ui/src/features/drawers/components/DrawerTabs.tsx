interface DrawerTabsProps {
  tabs: Array<{ id: string; label: string; novelty_label: string | null }>;
  active_tab: string;
  on_change: (tab_id: string) => void;
}

export function DrawerTabs({ tabs, active_tab, on_change }: DrawerTabsProps) {
  return (
    <div className="drawer-tabs" role="tablist" aria-label="Drawer tabs">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active_tab === tab.id}
          className={active_tab === tab.id ? "is-active" : ""}
          onClick={() => on_change(tab.id)}
        >
          <span>{tab.label}</span>
          {tab.novelty_label ? <span className="status-pill warning">{tab.novelty_label}</span> : null}
        </button>
      ))}
    </div>
  );
}

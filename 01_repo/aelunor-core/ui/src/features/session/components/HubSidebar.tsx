interface HubNavItem {
  label: string;
  icon: string;
  active?: boolean;
  disabled?: boolean;
}

const HUB_NAV_ITEMS: HubNavItem[] = [
  { label: "Hub", icon: "H", active: true },
  { label: "Campaign", icon: "C", disabled: true },
  { label: "Characters", icon: "P", disabled: true },
  { label: "World", icon: "W", disabled: true },
  { label: "Quests", icon: "Q", disabled: true },
  { label: "Inventory", icon: "I", disabled: true },
  { label: "Codex", icon: "X", disabled: true },
  { label: "Settings", icon: "S", disabled: true },
];

export function HubSidebar() {
  return (
    <aside className="hub-sidebar" aria-label="Aelunor Navigation">
      <div className="hub-sidebar-brand">
        <span className="hub-sidebar-mark" aria-hidden="true">
          <img src="/static/brand/aelunor-icon-512x512.png" alt="" />
        </span>
        <strong>AELUNOR</strong>
      </div>
      <nav className="hub-sidebar-nav" aria-label="Hub Bereiche">
        {HUB_NAV_ITEMS.map((item) => (
          <button
            key={item.label}
            type="button"
            className={`hub-sidebar-link${item.active ? " is-active" : ""}`}
            aria-current={item.active ? "page" : undefined}
            disabled={item.disabled}
            title={item.disabled ? `${item.label} ist im Hub noch nicht als Route aktiv.` : item.label}
          >
            <span className="hub-sidebar-icon" aria-hidden="true">
              {item.icon}
            </span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="hub-sidebar-footer" aria-hidden="true">
        <span />
      </div>
    </aside>
  );
}

interface HubNavItem {
  label: string;
  icon: string;
  icon_src?: string;
  active?: boolean;
  disabled?: boolean;
}

const HUB_NAV_ITEMS: HubNavItem[] = [
  { label: "Hub", icon: "H", icon_src: "/static/icons/hub_icon_sidebar.png", active: true },
  { label: "Campaign", icon: "C", icon_src: "/static/icons/campaign_icon_sidebar.png", disabled: true },
  { label: "Characters", icon: "P", icon_src: "/static/icons/characters_icon_png.png", disabled: true },
  { label: "World", icon: "W", icon_src: "/static/icons/world_icon_sidebar.png", disabled: true },
  { label: "Quests", icon: "Q", icon_src: "/static/icons/quests_icon_sidebar.png", disabled: true },
  { label: "Inventory", icon: "I", icon_src: "/static/icons/inventory_icon_sidebar.png", disabled: true },
  { label: "Codex", icon: "X", icon_src: "/static/icons/codex_icon_sidebar.png", disabled: true },
  { label: "Settings", icon: "S", icon_src: "/static/icons/settings_icon_sidebar.png", disabled: true },
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
            <span className={`hub-sidebar-icon${item.icon_src ? " has-image" : ""}`} aria-hidden="true">
              {item.icon_src ? <img src={item.icon_src} alt="" /> : item.icon}
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

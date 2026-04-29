import type { ReactNode } from "react";

export interface GameSidebarItem {
  id: string;
  label: string;
  detail?: string;
  active?: boolean;
  on_select: () => void;
}

interface GameSidebarProps {
  items: GameSidebarItem[];
  footer?: ReactNode;
}

export function GameSidebar({ items, footer }: GameSidebarProps) {
  return (
    <nav className="game-sidebar" aria-label="Aelunor Spielbereiche">
      <div className="game-sidebar-brand">
        <img src="/static/brand/aelunor-icon-512x512.png" alt="" />
        <span>Aelunor</span>
      </div>
      <div className="game-sidebar-items">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.active ? "game-sidebar-item is-active" : "game-sidebar-item"}
            onClick={item.on_select}
          >
            <span className="game-sidebar-rune" aria-hidden="true" />
            <span className="game-sidebar-copy">
              <span>{item.label}</span>
              {item.detail ? <small>{item.detail}</small> : null}
            </span>
          </button>
        ))}
      </div>
      {footer ? <div className="game-sidebar-footer">{footer}</div> : null}
    </nav>
  );
}

interface StatusBadgeProps {
  label: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "arcane";
}

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return <span className={`fantasy-status-badge is-${tone}`}>{label}</span>;
}

interface FantasyPanelProps {
  title?: string;
  meta?: string;
  className?: string;
  children: ReactNode;
}

export function FantasyPanel({ title, meta, className = "", children }: FantasyPanelProps) {
  return (
    <section className={`fantasy-panel ${className}`.trim()}>
      {title || meta ? (
        <div className="fantasy-panel-head">
          {title ? <h2>{title}</h2> : <span />}
          {meta ? <span>{meta}</span> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

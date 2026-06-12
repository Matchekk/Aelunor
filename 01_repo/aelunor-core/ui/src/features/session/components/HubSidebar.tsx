import { useEffect, useRef } from "react";

import type { V1AppPage } from "../../../app/routing/routes";

export type HubSidebarTarget = V1AppPage | "settings";

interface HubNavItem {
  id: HubSidebarTarget;
  label: string;
  icon: string;
  icon_src?: string;
}

const HUB_NAV_ITEMS: HubNavItem[] = [
  { id: "hub", label: "Hub", icon: "H", icon_src: "/v1/icons/hub_icon_sidebar.png" },
  { id: "campaigns", label: "Kampagnen", icon: "C", icon_src: "/v1/icons/campaign_icon_sidebar.png" },
  { id: "characters", label: "Figuren", icon: "P", icon_src: "/v1/icons/characters_icon_png.png" },
  { id: "world", label: "Welt", icon: "W", icon_src: "/v1/icons/world_icon_sidebar.png" },
  { id: "quests", label: "Quests", icon: "Q", icon_src: "/v1/icons/quests_icon_sidebar.png" },
  { id: "inventory", label: "Inventar", icon: "I", icon_src: "/v1/icons/inventory_icon_sidebar.png" },
  { id: "codex", label: "Kodex", icon: "X", icon_src: "/v1/icons/codex_icon_sidebar.png" },
  { id: "settings", label: "Einstellungen", icon: "S", icon_src: "/v1/icons/settings_icon_sidebar.png" },
];

function canDragSidebarNav(element: HTMLElement): boolean {
  const styles = window.getComputedStyle(element);
  return styles.gridAutoFlow === "column" && element.scrollWidth > element.clientWidth + 4;
}

interface HubSidebarProps {
  active_target: V1AppPage;
  on_select: (target: HubSidebarTarget, return_focus_element: HTMLElement | null) => void;
}

export function HubSidebar({ active_target, on_select }: HubSidebarProps) {
  const activeLinkRef = useRef<HTMLButtonElement | null>(null);
  const dragStateRef = useRef({
    animation_frame_id: 0,
    latest_delta_x: 0,
    pointer_id: -1,
    start_x: 0,
    scroll_left: 0,
  });
  const suppressClickRef = useRef(false);

  useEffect(() => {
    const element = activeLinkRef.current;
    if (!element || !canDragSidebarNav(element.parentElement as HTMLElement)) {
      return;
    }
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    element.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "nearest",
      inline: "center",
    });
  }, [active_target]);

  useEffect(() => {
    return () => {
      const animationFrameId = dragStateRef.current.animation_frame_id;
      if (animationFrameId) {
        window.cancelAnimationFrame(animationFrameId);
      }
    };
  }, []);

  const stopDrag = (element: HTMLElement, pointer_id: number) => {
    if (dragStateRef.current.pointer_id !== pointer_id) {
      return;
    }
    const animationFrameId = dragStateRef.current.animation_frame_id;
    if (animationFrameId) {
      window.cancelAnimationFrame(animationFrameId);
      dragStateRef.current.animation_frame_id = 0;
      element.scrollLeft = dragStateRef.current.scroll_left - dragStateRef.current.latest_delta_x;
    }
    element.classList.remove("is-dragging");
    if (element.hasPointerCapture(pointer_id)) {
      element.releasePointerCapture(pointer_id);
    }
    dragStateRef.current.pointer_id = -1;
  };

  const scheduleDragScroll = (element: HTMLElement) => {
    if (dragStateRef.current.animation_frame_id) {
      return;
    }
    dragStateRef.current.animation_frame_id = window.requestAnimationFrame(() => {
      dragStateRef.current.animation_frame_id = 0;
      element.scrollLeft = dragStateRef.current.scroll_left - dragStateRef.current.latest_delta_x;
    });
  };

  return (
    <aside className="hub-sidebar" aria-label="Aelunor Navigation">
      <div className="hub-sidebar-brand">
        <span className="hub-sidebar-mark" aria-hidden="true">
          <img src="/v1/brand/aelunor-icon-512x512.png" alt="" />
        </span>
        <strong>AELUNOR</strong>
      </div>
      <nav
        className="hub-sidebar-nav"
        aria-label="Hub Bereiche"
        onPointerDown={(event) => {
          suppressClickRef.current = false;
          if (event.button !== 0 || !canDragSidebarNav(event.currentTarget)) {
            return;
          }
          dragStateRef.current = {
            animation_frame_id: 0,
            latest_delta_x: 0,
            pointer_id: event.pointerId,
            start_x: event.clientX,
            scroll_left: event.currentTarget.scrollLeft,
          };
          suppressClickRef.current = false;
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          const dragState = dragStateRef.current;
          if (dragState.pointer_id !== event.pointerId) {
            return;
          }
          const deltaX = event.clientX - dragState.start_x;
          if (Math.abs(deltaX) > 4) {
            suppressClickRef.current = true;
            event.currentTarget.classList.add("is-dragging");
          }
          dragState.latest_delta_x = deltaX;
          scheduleDragScroll(event.currentTarget);
        }}
        onPointerUp={(event) => {
          stopDrag(event.currentTarget, event.pointerId);
        }}
        onPointerCancel={(event) => {
          stopDrag(event.currentTarget, event.pointerId);
        }}
      >
        {HUB_NAV_ITEMS.map((item) => (
          <button
            key={item.label}
            type="button"
            ref={item.id === active_target ? activeLinkRef : undefined}
            className={`hub-sidebar-link${item.id === active_target ? " is-active" : ""}`}
            aria-current={item.id === active_target ? "page" : undefined}
            title={item.label}
            onClick={(event) => {
              if (suppressClickRef.current) {
                event.preventDefault();
                event.stopPropagation();
                suppressClickRef.current = false;
                return;
              }
              on_select(item.id, event.currentTarget);
            }}
          >
            <span className={`hub-sidebar-icon${item.icon_src ? " has-image" : ""}`} aria-hidden="true">
              {item.icon_src ? <img src={item.icon_src} alt="" /> : item.icon}
            </span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}

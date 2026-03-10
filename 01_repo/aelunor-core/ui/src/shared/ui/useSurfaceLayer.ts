import { useEffect, useId } from "react";

import { useSurfaceStackStore, type SurfaceKind } from "./surfaceStack";

interface UseSurfaceLayerOptions {
  open: boolean;
  kind: SurfaceKind;
  priority: number;
  container: HTMLElement | null;
  return_focus_element?: HTMLElement | null;
  close_on_escape?: boolean;
  on_close?: () => void;
  trap_focus?: boolean;
  lock_scroll?: boolean;
}

function collectFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => !element.hasAttribute("disabled") && !element.getAttribute("aria-hidden"));
}

let bodyLockCount = 0;
let previousOverflow = "";

function lockBodyScroll(): void {
  if (typeof document === "undefined") {
    return;
  }
  if (bodyLockCount === 0) {
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  }
  bodyLockCount += 1;
}

function unlockBodyScroll(): void {
  if (typeof document === "undefined" || bodyLockCount === 0) {
    return;
  }
  bodyLockCount -= 1;
  if (bodyLockCount === 0) {
    document.body.style.overflow = previousOverflow;
  }
}

export function useSurfaceLayer({
  open,
  kind,
  priority,
  container,
  return_focus_element = null,
  close_on_escape = true,
  on_close,
  trap_focus = true,
  lock_scroll = true,
}: UseSurfaceLayerOptions): string {
  const generatedId = useId();
  const surface_id = `${kind}-${generatedId}`;
  const register_surface = useSurfaceStackStore((state) => state.register_surface);
  const unregister_surface = useSurfaceStackStore((state) => state.unregister_surface);
  const top_surface_id = useSurfaceStackStore((state) => state.top_surface_id);
  const is_top_surface = open && top_surface_id === surface_id;

  useEffect(() => {
    if (!open) {
      return;
    }

    register_surface({
      surface_id,
      kind,
      priority,
    });

    if (lock_scroll) {
      lockBodyScroll();
    }

    return () => {
      const nextTopSurfaceId = unregister_surface(surface_id);
      if (lock_scroll) {
        unlockBodyScroll();
      }
      if (!nextTopSurfaceId) {
        return_focus_element?.focus();
      }
    };
  }, [kind, lock_scroll, open, priority, register_surface, return_focus_element, surface_id, unregister_surface]);

  useEffect(() => {
    if (!open || !is_top_surface || !container) {
      return;
    }

    if (!container.hasAttribute("tabindex")) {
      container.setAttribute("tabindex", "-1");
    }

    const focusable = collectFocusable(container);
    (focusable[0] ?? container).focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && close_on_escape && on_close) {
        event.preventDefault();
        on_close();
        return;
      }

      if (event.key !== "Tab" || !trap_focus) {
        return;
      }

      const nodes = collectFocusable(container);
      if (nodes.length === 0) {
        event.preventDefault();
        container.focus();
        return;
      }

      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (!first || !last) {
        event.preventDefault();
        return;
      }

      const active = document.activeElement;
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [close_on_escape, container, is_top_surface, on_close, open, trap_focus]);

  return surface_id;
}

import { create } from "zustand";

export type SurfaceKind = "modal" | "drawer";

interface SurfaceEntry {
  surface_id: string;
  priority: number;
  kind: SurfaceKind;
  order: number;
}

interface SurfaceStackState {
  entries: SurfaceEntry[];
  top_surface_id: string | null;
  register_surface: (surface: Omit<SurfaceEntry, "order">) => void;
  unregister_surface: (surface_id: string) => string | null;
}

let nextSurfaceOrder = 1;

function sortEntries(entries: SurfaceEntry[]): SurfaceEntry[] {
  return [...entries].sort((left, right) => {
    if (left.priority !== right.priority) {
      return left.priority - right.priority;
    }
    return left.order - right.order;
  });
}

function deriveTopSurfaceId(entries: SurfaceEntry[]): string | null {
  const ordered = sortEntries(entries);
  return ordered.length > 0 ? ordered[ordered.length - 1]?.surface_id ?? null : null;
}

export const useSurfaceStackStore = create<SurfaceStackState>((set, get) => ({
  entries: [],
  top_surface_id: null,
  register_surface: (surface) => {
    set((state) => {
      const existing = state.entries.filter((entry) => entry.surface_id !== surface.surface_id);
      const nextEntries = [
        ...existing,
        {
          ...surface,
          order: nextSurfaceOrder++,
        },
      ];
      return {
        entries: nextEntries,
        top_surface_id: deriveTopSurfaceId(nextEntries),
      };
    });
  },
  unregister_surface: (surface_id) => {
    const nextEntries = get().entries.filter((entry) => entry.surface_id !== surface_id);
    const top_surface_id = deriveTopSurfaceId(nextEntries);
    set({
      entries: nextEntries,
      top_surface_id,
    });
    return top_surface_id;
  },
}));

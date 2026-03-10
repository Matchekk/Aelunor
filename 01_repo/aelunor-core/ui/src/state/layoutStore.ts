import { create } from "zustand";

interface LayoutStoreState {
  rightRailOpen: boolean;
  setRightRailOpen: (is_open: boolean) => void;
  toggleRightRail: () => void;
}

export const useLayoutStore = create<LayoutStoreState>((set) => ({
  rightRailOpen: true,
  setRightRailOpen: (is_open) => set({ rightRailOpen: is_open }),
  toggleRightRail: () => set((state) => ({ rightRailOpen: !state.rightRailOpen })),
}));

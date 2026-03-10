import { create } from "zustand";

import type {
  PresenceActivity,
  PresenceBlockingAction,
  PresenceState,
} from "../../shared/api/contracts";

interface PresenceStoreState {
  sseConnected: boolean;
  activities: Record<string, PresenceActivity>;
  blockingAction: PresenceBlockingAction | null;
  version: number;
  setSseConnected: (connected: boolean) => void;
  applyPresenceSync: (snapshot: PresenceState) => void;
  resetPresence: () => void;
}

const initialPresenceState = {
  sseConnected: false,
  activities: {},
  blockingAction: null,
  version: 0,
};

export const usePresenceStore = create<PresenceStoreState>((set) => ({
  ...initialPresenceState,
  setSseConnected: (connected) => {
    set({ sseConnected: connected });
  },
  applyPresenceSync: (snapshot) => {
    set({
      activities: snapshot.activities ?? {},
      blockingAction: snapshot.blocking_action ?? null,
      version: Number.isFinite(snapshot.version) ? snapshot.version : 0,
    });
  },
  resetPresence: () => {
    set(initialPresenceState);
  },
}));

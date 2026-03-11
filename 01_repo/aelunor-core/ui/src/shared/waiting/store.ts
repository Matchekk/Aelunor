import { create } from "zustand";

import type { WaitingSignal, WaitingSignalInput } from "./model";

interface WaitingStoreState {
  signals: WaitingSignal[];
  upsert_signal: (signal: WaitingSignalInput) => void;
  clear_signal: (key: string) => void;
  clear_all: () => void;
}

function toSignal(input: WaitingSignalInput, now: number, existing: WaitingSignal | null): WaitingSignal {
  return {
    key: input.key,
    context: input.context,
    scope: input.scope,
    blocking_level: input.blocking_level,
    surface_target: input.surface_target,
    message_override: input.message_override ?? null,
    detail_override: input.detail_override ?? null,
    started_at: existing?.started_at ?? now,
  };
}

export const useWaitingStore = create<WaitingStoreState>((set) => ({
  signals: [],
  upsert_signal: (input) =>
    set((state) => {
      const existing = state.signals.find((entry) => entry.key === input.key) ?? null;
      const nextSignal = toSignal(input, Date.now(), existing);
      const withoutCurrent = state.signals.filter((entry) => entry.key !== input.key);
      return {
        signals: [...withoutCurrent, nextSignal],
      };
    }),
  clear_signal: (key) =>
    set((state) => ({
      signals: state.signals.filter((entry) => entry.key !== key),
    })),
  clear_all: () => set({ signals: [] }),
}));

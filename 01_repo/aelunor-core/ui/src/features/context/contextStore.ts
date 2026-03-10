import { create } from "zustand";

import type { ContextQueryResponse } from "../../shared/api/contracts";

interface ContextStoreState {
  open: boolean;
  payload: ContextQueryResponse | null;
  return_focus_element: HTMLElement | null;
  open_context: (payload: ContextQueryResponse, return_focus?: HTMLElement | null) => void;
  close_context: () => void;
}

export const useContextStore = create<ContextStoreState>((set) => ({
  open: false,
  payload: null,
  return_focus_element: null,
  open_context: (payload, return_focus = null) =>
    set({
      open: true,
      payload,
      return_focus_element: return_focus,
    }),
  close_context: () =>
    set({
      open: false,
      payload: null,
      return_focus_element: null,
    }),
}));

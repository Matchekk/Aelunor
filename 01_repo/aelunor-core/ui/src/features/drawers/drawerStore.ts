import { create } from "zustand";

export type DrawerType = "character" | "npc" | "codex";
export type CodexKind = "race" | "beast";

interface DrawerStoreState {
  drawer_open: boolean;
  drawer_type: DrawerType | null;
  drawer_entity_id: string | null;
  drawer_codex_kind: CodexKind | null;
  active_drawer_tab: string;
  return_focus_element: HTMLElement | null;
  open_character: (slot_id: string, tab_id?: string, return_focus?: HTMLElement | null) => void;
  open_npc: (npc_id: string, tab_id?: string, return_focus?: HTMLElement | null) => void;
  open_codex: (kind: CodexKind, entity_id: string, tab_id?: string, return_focus?: HTMLElement | null) => void;
  close_drawer: () => void;
  set_active_tab: (tab_id: string) => void;
}

export const useDrawerStore = create<DrawerStoreState>((set) => ({
  drawer_open: false,
  drawer_type: null,
  drawer_entity_id: null,
  drawer_codex_kind: null,
  active_drawer_tab: "overview",
  return_focus_element: null,
  open_character: (slot_id, tab_id = "overview", return_focus = null) =>
    set({
      drawer_open: true,
      drawer_type: "character",
      drawer_entity_id: slot_id,
      drawer_codex_kind: null,
      active_drawer_tab: tab_id,
      return_focus_element: return_focus,
    }),
  open_npc: (npc_id, tab_id = "overview", return_focus = null) =>
    set({
      drawer_open: true,
      drawer_type: "npc",
      drawer_entity_id: npc_id,
      drawer_codex_kind: null,
      active_drawer_tab: tab_id,
      return_focus_element: return_focus,
    }),
  open_codex: (kind, entity_id, tab_id = "overview", return_focus = null) =>
    set({
      drawer_open: true,
      drawer_type: "codex",
      drawer_entity_id: entity_id,
      drawer_codex_kind: kind,
      active_drawer_tab: tab_id,
      return_focus_element: return_focus,
    }),
  close_drawer: () =>
    set({
      drawer_open: false,
      drawer_type: null,
      drawer_entity_id: null,
      drawer_codex_kind: null,
      active_drawer_tab: "overview",
      return_focus_element: null,
    }),
  set_active_tab: (tab_id) => set({ active_drawer_tab: tab_id }),
}));

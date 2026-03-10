import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import type { ThemeState } from "../../shared/api/contracts";
import type { FontPresetId, FontSizeId, ThemeId } from "../../shared/types/domain";

const LEGACY_THEME_KEY = "isekaiTheme";
const LEGACY_FONT_PRESET_KEY = "isekaiFontPreset";
const LEGACY_FONT_SIZE_KEY = "isekaiFontSize";
const THEME_STORE_KEY = "isekaiThemeStateV1";

const THEME_IDS: ThemeId[] = ["arcane", "tavern", "glade", "hybrid"];
const FONT_PRESET_IDS: FontPresetId[] = ["classic", "clean", "literary"];
const FONT_SIZE_IDS: FontSizeId[] = ["small", "medium", "large"];

interface ThemeStoreState extends ThemeState {
  setTheme: (theme: ThemeId) => void;
  setFontPreset: (font_preset: FontPresetId) => void;
  setFontSize: (font_size: FontSizeId) => void;
}

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function resolveThemeId(value: string | null): ThemeId {
  return THEME_IDS.includes(value as ThemeId) ? (value as ThemeId) : "arcane";
}

function resolveFontPresetId(value: string | null): FontPresetId {
  return FONT_PRESET_IDS.includes(value as FontPresetId) ? (value as FontPresetId) : "classic";
}

function resolveFontSizeId(value: string | null): FontSizeId {
  return FONT_SIZE_IDS.includes(value as FontSizeId) ? (value as FontSizeId) : "medium";
}

function readLegacyThemeState(): ThemeState {
  const storage = getStorage();
  if (!storage) {
    return {
      theme: "arcane",
      font_preset: "classic",
      font_size: "medium",
    };
  }
  return {
    theme: resolveThemeId(storage.getItem(LEGACY_THEME_KEY)),
    font_preset: resolveFontPresetId(storage.getItem(LEGACY_FONT_PRESET_KEY)),
    font_size: resolveFontSizeId(storage.getItem(LEGACY_FONT_SIZE_KEY)),
  };
}

function syncLegacyThemeState(state: ThemeState): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.setItem(LEGACY_THEME_KEY, state.theme);
  storage.setItem(LEGACY_FONT_PRESET_KEY, state.font_preset);
  storage.setItem(LEGACY_FONT_SIZE_KEY, state.font_size);
}

const noOpStorage: StateStorage = {
  getItem: () => null,
  setItem: () => undefined,
  removeItem: () => undefined,
};

export const useThemeStore = create<ThemeStoreState>()(
  persist(
    (set, get) => ({
      ...readLegacyThemeState(),
      setTheme: (theme) => {
        set({ theme });
        syncLegacyThemeState({ ...get(), theme });
      },
      setFontPreset: (font_preset) => {
        set({ font_preset });
        syncLegacyThemeState({ ...get(), font_preset });
      },
      setFontSize: (font_size) => {
        set({ font_size });
        syncLegacyThemeState({ ...get(), font_size });
      },
    }),
    {
      name: THEME_STORE_KEY,
      storage: createJSONStorage(() => getStorage() ?? noOpStorage),
      partialize: (state) => ({
        theme: state.theme,
        font_preset: state.font_preset,
        font_size: state.font_size,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) {
          return;
        }
        syncLegacyThemeState({
          theme: state.theme,
          font_preset: state.font_preset,
          font_size: state.font_size,
        });
      },
    },
  ),
);

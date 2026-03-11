import type { ThemeState } from "../../shared/api/contracts";
import type { FontPresetId, FontSizeId, ThemeId } from "../../shared/types/domain";
import { useUserSettingsStore } from "../settings/store";

interface ThemeStoreState extends ThemeState {
  setTheme: (theme: ThemeId) => void;
  setFontPreset: (font_preset: FontPresetId) => void;
  setFontSize: (font_size: FontSizeId) => void;
}

export function useThemeStore<T>(selector: (state: ThemeStoreState) => T): T {
  return useUserSettingsStore((state) =>
    selector({
      theme: state.appearance.theme,
      font_preset: state.appearance.font_preset,
      font_size: state.appearance.font_size,
      setTheme: state.set_theme,
      setFontPreset: state.set_font_preset,
      setFontSize: state.set_font_size,
    }),
  );
}

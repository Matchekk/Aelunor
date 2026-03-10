import { useEffect, type ReactNode } from "react";

import { useThemeStore } from "../../entities/theme/store";

const THEME_CLASSES = ["theme-arcane", "theme-tavern", "theme-glade", "theme-hybrid"];

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const { theme, font_preset, font_size } = useThemeStore((state) => ({
    theme: state.theme,
    font_preset: state.font_preset,
    font_size: state.font_size,
  }));

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.fontPreset = font_preset;
    root.dataset.fontSize = font_size;
    root.classList.remove(...THEME_CLASSES);
    root.classList.add(`theme-${theme}`);
  }, [font_preset, font_size, theme]);

  return <>{children}</>;
}

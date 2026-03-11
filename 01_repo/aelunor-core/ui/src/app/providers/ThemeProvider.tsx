import { useEffect, type ReactNode } from "react";

import { useUserSettingsStore } from "../../entities/settings/store";

const THEME_CLASSES = ["theme-arcane", "theme-tavern", "theme-glade", "theme-hybrid"];

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const { appearance, accessibility, locale } = useUserSettingsStore((state) => ({
    appearance: state.appearance,
    accessibility: state.accessibility,
    locale: state.locale,
  }));

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = appearance.theme;
    root.dataset.fontPreset = appearance.font_preset;
    root.dataset.fontSize = appearance.font_size;
    root.dataset.density = appearance.density;
    root.dataset.storyWidth = appearance.story_width;
    root.dataset.reducedMotion = accessibility.reduced_motion ? "true" : "false";
    root.dataset.highContrast = accessibility.high_contrast ? "true" : "false";
    root.dataset.strongFocus = accessibility.strong_focus ? "true" : "false";
    root.dataset.largerTargets = accessibility.larger_targets ? "true" : "false";
    root.dataset.readingFriendly = accessibility.reading_friendly_mode ? "true" : "false";
    root.lang = locale.language === "en" ? "en" : "de";
    root.classList.remove(...THEME_CLASSES);
    root.classList.add(`theme-${appearance.theme}`);
  }, [appearance, accessibility, locale.language]);

  return <>{children}</>;
}

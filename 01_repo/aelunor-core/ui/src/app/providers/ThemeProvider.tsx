import { useEffect, type ReactNode } from "react";

import { fontSizeLabelToPx } from "../../entities/settings/fontSize";
import { useUserSettingsStore } from "../../entities/settings/store";

const THEME_CLASSES = ["theme-arcane", "theme-tavern", "theme-glade", "theme-hybrid"];

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const { appearance, reading, accessibility, locale } = useUserSettingsStore((state) => ({
    appearance: state.appearance,
    reading: state.reading,
    accessibility: state.accessibility,
    locale: state.locale,
  }));

  useEffect(() => {
    const root = document.documentElement;
    const fontSizePx = fontSizeLabelToPx(reading.textSize);
    const lineHeight = reading.storyLineHeight === "spacious" ? "1.78" : reading.storyLineHeight === "normal" ? "1.5" : "1.62";
    root.dataset.theme = appearance.theme;
    root.dataset.themeMode = appearance.themeMode;
    root.dataset.fontPreset = reading.fontPreset;
    root.dataset.fontSize = String(fontSizePx);
    root.dataset.readingTextSize = reading.textSize;
    root.dataset.storyLineHeight = reading.storyLineHeight;
    root.style.setProperty("--v1-font-size-base", `${fontSizePx}px`);
    root.style.setProperty("--v1-story-line-height", lineHeight);
    root.dataset.uiDensity = appearance.uiDensity;
    root.dataset.glowIntensity = appearance.glowIntensity;
    root.dataset.locationThemeMode = appearance.locationThemeMode;
    root.dataset.fixedLocationTheme = appearance.fixedLocationTheme;
    root.dataset.density = appearance.density;
    root.dataset.storyWidth = appearance.story_width;
    root.dataset.reducedMotion = appearance.reducedMotion || accessibility.reduced_motion ? "true" : "false";
    root.dataset.highContrast = accessibility.high_contrast ? "true" : "false";
    root.dataset.strongFocus = accessibility.strong_focus ? "true" : "false";
    root.dataset.largerTargets = accessibility.larger_targets ? "true" : "false";
    root.dataset.readingFriendly = accessibility.reading_friendly_mode ? "true" : "false";
    root.lang = locale.language === "en" ? "en" : "de";
    root.classList.remove(...THEME_CLASSES);
    root.classList.add(`theme-${appearance.theme}`);
  }, [appearance, reading, accessibility, locale.language]);

  return <>{children}</>;
}

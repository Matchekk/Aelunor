import { create } from "zustand";

import type { ThemeId, FontPresetId, FontSizeId } from "../../shared/types/domain";
import type {
  AccessibilitySettings,
  AppearanceSettings,
  ComposerModePreference,
  DateFormatId,
  InteractionSettings,
  LanguageId,
  LocaleSettings,
  NotificationSettings,
  NumberFormatId,
  StoryWidthId,
  TimeFormatId,
  TimelineDetailDefault,
  TooltipIntensity,
  UiDensityId,
  UserSettings,
} from "./types";
import { clearLocalComfortData } from "./localData";
import { migrateSettings, resolveSettingsDefaults } from "./schema";

const SETTINGS_STORAGE_KEY = "aelunorUserSettingsV1";
const LEGACY_THEME_STORE_KEY = "isekaiThemeStateV1";
const LEGACY_THEME_KEY = "isekaiTheme";
const LEGACY_FONT_PRESET_KEY = "isekaiFontPreset";
const LEGACY_FONT_SIZE_KEY = "isekaiFontSize";

const THEME_IDS: ThemeId[] = ["arcane", "tavern", "glade", "hybrid"];
const FONT_PRESET_IDS: FontPresetId[] = ["classic", "clean", "literary"];
const FONT_SIZE_IDS: FontSizeId[] = ["small", "medium", "large"];

interface UserSettingsStoreState extends UserSettings {
  patch_appearance: (patch: Partial<AppearanceSettings>) => void;
  patch_interaction: (patch: Partial<InteractionSettings>) => void;
  patch_accessibility: (patch: Partial<AccessibilitySettings>) => void;
  patch_locale: (patch: Partial<LocaleSettings>) => void;
  patch_notifications: (patch: Partial<NotificationSettings>) => void;
  set_theme: (theme: ThemeId) => void;
  set_font_preset: (font_preset: FontPresetId) => void;
  set_font_size: (font_size: FontSizeId) => void;
  set_density: (density: UiDensityId) => void;
  set_story_width: (story_width: StoryWidthId) => void;
  set_auto_scroll: (auto_scroll: boolean) => void;
  set_confirm_leave: (confirm_leave: boolean) => void;
  set_remember_filters: (remember_filters: boolean) => void;
  set_timeline_detail_default: (timeline_detail_default: TimelineDetailDefault) => void;
  set_shortcuts_enabled: (shortcuts_enabled: boolean) => void;
  set_shortcut_hints: (shortcut_hints: boolean) => void;
  set_composer_mode_preference: (composer_mode_preference: ComposerModePreference) => void;
  set_tooltip_intensity: (tooltip_intensity: TooltipIntensity) => void;
  set_reduced_motion: (reduced_motion: boolean) => void;
  set_high_contrast: (high_contrast: boolean) => void;
  set_strong_focus: (strong_focus: boolean) => void;
  set_larger_targets: (larger_targets: boolean) => void;
  set_reading_friendly_mode: (reading_friendly_mode: boolean) => void;
  set_language: (language: LanguageId) => void;
  set_time_format: (time_format: TimeFormatId) => void;
  set_date_format: (date_format: DateFormatId) => void;
  set_number_format: (number_format: NumberFormatId) => void;
  reset_settings: () => void;
  clear_local_comfort_data: () => void;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function localStorageSafe(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function persistSnapshot(snapshot: UserSettings, storage_override: Storage | null = null): void {
  const storage = storage_override ?? localStorageSafe();
  if (!storage) {
    return;
  }
  storage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(snapshot));
}

function isTheme(value: unknown): value is ThemeId {
  return typeof value === "string" && THEME_IDS.includes(value as ThemeId);
}

function isFontPreset(value: unknown): value is FontPresetId {
  return typeof value === "string" && FONT_PRESET_IDS.includes(value as FontPresetId);
}

function isFontSize(value: unknown): value is FontSizeId {
  return typeof value === "string" && FONT_SIZE_IDS.includes(value as FontSizeId);
}

export function readLegacyAppearanceFromStorage(storage: Storage | null): Partial<AppearanceSettings> {
  if (!storage) {
    return {};
  }

  let themeCandidate: unknown = storage.getItem(LEGACY_THEME_KEY);
  let fontPresetCandidate: unknown = storage.getItem(LEGACY_FONT_PRESET_KEY);
  let fontSizeCandidate: unknown = storage.getItem(LEGACY_FONT_SIZE_KEY);

  const legacyStoreRaw = storage.getItem(LEGACY_THEME_STORE_KEY);
  if (legacyStoreRaw) {
    try {
      const parsed = JSON.parse(legacyStoreRaw) as unknown;
      const state = "state" in readRecord(parsed) ? readRecord(readRecord(parsed).state) : readRecord(parsed);
      if (!themeCandidate) {
        themeCandidate = state.theme;
      }
      if (!fontPresetCandidate) {
        fontPresetCandidate = state.font_preset;
      }
      if (!fontSizeCandidate) {
        fontSizeCandidate = state.font_size;
      }
    } catch {
      // Ignore malformed legacy payload.
    }
  }

  const next: Partial<AppearanceSettings> = {};
  if (isTheme(themeCandidate)) {
    next.theme = themeCandidate;
  }
  if (isFontPreset(fontPresetCandidate)) {
    next.font_preset = fontPresetCandidate;
  }
  if (isFontSize(fontSizeCandidate)) {
    next.font_size = fontSizeCandidate;
  }
  return next;
}

function syncLegacyAppearance(appearance: AppearanceSettings, storage_override: Storage | null = null): void {
  const storage = storage_override ?? localStorageSafe();
  if (!storage) {
    return;
  }
  storage.setItem(LEGACY_THEME_KEY, appearance.theme);
  storage.setItem(LEGACY_FONT_PRESET_KEY, appearance.font_preset);
  storage.setItem(LEGACY_FONT_SIZE_KEY, appearance.font_size);
}

export function resolveInitialSettingsFromStorage(storage: Storage | null): UserSettings {
  const defaults = resolveSettingsDefaults();
  if (!storage) {
    return defaults;
  }

  const raw = storage.getItem(SETTINGS_STORAGE_KEY);
  if (raw) {
    try {
      const migrated = migrateSettings(JSON.parse(raw) as unknown);
      syncLegacyAppearance(migrated.appearance, storage);
      persistSnapshot(migrated, storage);
      return migrated;
    } catch {
      // Continue with defaults + legacy recovery.
    }
  }

  const legacyAppearance = readLegacyAppearanceFromStorage(storage);
  const recovered: UserSettings = migrateSettings({
    ...defaults,
    appearance: {
      ...defaults.appearance,
      ...legacyAppearance,
    },
  });
  syncLegacyAppearance(recovered.appearance, storage);
  persistSnapshot(recovered, storage);
  return recovered;
}

function snapshotFromState(state: UserSettingsStoreState): UserSettings {
  return {
    appearance: state.appearance,
    interaction: state.interaction,
    accessibility: state.accessibility,
    locale: state.locale,
    notifications: state.notifications,
    local_data_meta: state.local_data_meta,
    meta: state.meta,
  };
}

function updateStore(
  set: (fn: (state: UserSettingsStoreState) => UserSettingsStoreState) => void,
  updater: (state: UserSettingsStoreState) => UserSettingsStoreState,
): void {
  set((state) => {
    const next = updater(state);
    persistSnapshot(snapshotFromState(next));
    syncLegacyAppearance(next.appearance);
    return next;
  });
}

const initialSettings = resolveInitialSettingsFromStorage(localStorageSafe());

export const useUserSettingsStore = create<UserSettingsStoreState>((set) => ({
  ...initialSettings,
  patch_appearance: (patch) => {
    updateStore(set, (state) => ({
      ...state,
      appearance: {
        ...state.appearance,
        ...patch,
      },
    }));
  },
  patch_interaction: (patch) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        ...patch,
      },
    }));
  },
  patch_accessibility: (patch) => {
    updateStore(set, (state) => ({
      ...state,
      accessibility: {
        ...state.accessibility,
        ...patch,
      },
    }));
  },
  patch_locale: (patch) => {
    updateStore(set, (state) => ({
      ...state,
      locale: {
        ...state.locale,
        ...patch,
      },
    }));
  },
  patch_notifications: (patch) => {
    updateStore(set, (state) => ({
      ...state,
      notifications: {
        ...state.notifications,
        ...patch,
      },
    }));
  },
  set_theme: (theme) => {
    updateStore(set, (state) => ({
      ...state,
      appearance: {
        ...state.appearance,
        theme,
      },
    }));
  },
  set_font_preset: (font_preset) => {
    updateStore(set, (state) => ({
      ...state,
      appearance: {
        ...state.appearance,
        font_preset,
      },
    }));
  },
  set_font_size: (font_size) => {
    updateStore(set, (state) => ({
      ...state,
      appearance: {
        ...state.appearance,
        font_size,
      },
    }));
  },
  set_density: (density) => {
    updateStore(set, (state) => ({
      ...state,
      appearance: {
        ...state.appearance,
        density,
      },
    }));
  },
  set_story_width: (story_width) => {
    updateStore(set, (state) => ({
      ...state,
      appearance: {
        ...state.appearance,
        story_width,
      },
    }));
  },
  set_auto_scroll: (auto_scroll) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        auto_scroll,
      },
    }));
  },
  set_confirm_leave: (confirm_leave) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        confirm_leave,
      },
    }));
  },
  set_remember_filters: (remember_filters) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        remember_filters,
      },
    }));
  },
  set_timeline_detail_default: (timeline_detail_default) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        timeline_detail_default,
      },
    }));
  },
  set_shortcuts_enabled: (shortcuts_enabled) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        shortcuts_enabled,
      },
    }));
  },
  set_shortcut_hints: (shortcut_hints) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        shortcut_hints,
      },
    }));
  },
  set_composer_mode_preference: (composer_mode_preference) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        composer_mode_preference,
      },
    }));
  },
  set_tooltip_intensity: (tooltip_intensity) => {
    updateStore(set, (state) => ({
      ...state,
      interaction: {
        ...state.interaction,
        tooltip_intensity,
      },
    }));
  },
  set_reduced_motion: (reduced_motion) => {
    updateStore(set, (state) => ({
      ...state,
      accessibility: {
        ...state.accessibility,
        reduced_motion,
      },
    }));
  },
  set_high_contrast: (high_contrast) => {
    updateStore(set, (state) => ({
      ...state,
      accessibility: {
        ...state.accessibility,
        high_contrast,
      },
    }));
  },
  set_strong_focus: (strong_focus) => {
    updateStore(set, (state) => ({
      ...state,
      accessibility: {
        ...state.accessibility,
        strong_focus,
      },
    }));
  },
  set_larger_targets: (larger_targets) => {
    updateStore(set, (state) => ({
      ...state,
      accessibility: {
        ...state.accessibility,
        larger_targets,
      },
    }));
  },
  set_reading_friendly_mode: (reading_friendly_mode) => {
    updateStore(set, (state) => ({
      ...state,
      accessibility: {
        ...state.accessibility,
        reading_friendly_mode,
      },
    }));
  },
  set_language: (language) => {
    updateStore(set, (state) => ({
      ...state,
      locale: {
        ...state.locale,
        language,
      },
    }));
  },
  set_time_format: (time_format) => {
    updateStore(set, (state) => ({
      ...state,
      locale: {
        ...state.locale,
        time_format,
      },
    }));
  },
  set_date_format: (date_format) => {
    updateStore(set, (state) => ({
      ...state,
      locale: {
        ...state.locale,
        date_format,
      },
    }));
  },
  set_number_format: (number_format) => {
    updateStore(set, (state) => ({
      ...state,
      locale: {
        ...state.locale,
        number_format,
      },
    }));
  },
  reset_settings: () => {
    updateStore(set, (state) => ({
      ...state,
      ...resolveSettingsDefaults(),
    }));
  },
  clear_local_comfort_data: () => {
    clearLocalComfortData();
  },
}));

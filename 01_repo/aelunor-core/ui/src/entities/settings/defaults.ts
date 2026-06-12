import type {
  AppearanceSettings,
  DiagnosticsSettings,
  GameplaySettings,
  GmSettings,
  InteractionSettings,
  LocaleSettings,
  NotificationSettings,
  PrivacySettings,
  ReadingSettings,
  UserSettings,
} from "./types";
import { FONT_SIZE_DEFAULT_PX } from "./fontSize";

export const USER_SETTINGS_SCHEMA_VERSION = 4;

export function resolveSettingsDefaults(): UserSettings {
  const gm: GmSettings = {
    provider: "ollama",
    ollamaBaseUrl: "http://127.0.0.1:11434",
    model: null,
    style: "balanced",
    responseLength: "normal",
    canonStrictness: "normal",
  };

  const reading: ReadingSettings = {
    fontPreset: "aelunor-classic",
    textSize: "medium",
    storyLineHeight: "comfortable",
  };

  const appearance: AppearanceSettings = {
    themeMode: "aelunor-dark",
    locationThemeMode: "automatic",
    fixedLocationTheme: "default",
    uiDensity: "comfortable",
    glowIntensity: "normal",
    reducedMotion: false,
    theme: "hybrid",
    font_preset: reading.fontPreset,
    font_size: FONT_SIZE_DEFAULT_PX,
    density: "comfortable",
    story_width: "standard",
  };

  const gameplay: GameplaySettings = {
    turnMode: "balanced",
    randomness: "normal",
    showHints: true,
    autoSummaryTurns: 20,
  };

  const privacy: PrivacySettings = {
    preferLocalModels: true,
    allowExternalApiCalls: false,
    anonymizeDiagnostics: true,
  };

  const diagnostics: DiagnosticsSettings = {
    showDeveloperPanel: false,
  };

  const interaction: InteractionSettings = {
    auto_scroll: true,
    confirm_leave: true,
    remember_filters: true,
    timeline_detail_default: "collapsed",
    shortcuts_enabled: true,
    shortcut_hints: true,
    composer_mode_preference: "do",
    tooltip_intensity: "standard",
  };

  const locale: LocaleSettings = {
    language: "de",
    time_format: "24h",
    date_format: "locale",
    number_format: "locale",
  };

  const notifications: NotificationSettings = {
    ui_sound: false,
    sound_volume: 60,
    desktop_notifications: false,
  };

  return {
    gm,
    appearance,
    reading,
    gameplay,
    privacy,
    diagnostics,
    interaction,
    accessibility: {
      reduced_motion: false,
      high_contrast: false,
      strong_focus: false,
      larger_targets: false,
      reading_friendly_mode: false,
    },
    locale,
    notifications,
    local_data_meta: {
      resettable_local_names: true,
      resettable_drafts: true,
      resettable_filters: true,
    },
    meta: {
      schema_version: USER_SETTINGS_SCHEMA_VERSION,
    },
  };
}

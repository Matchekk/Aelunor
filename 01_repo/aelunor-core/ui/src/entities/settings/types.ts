import type { FontPresetId, FontSizeId, ThemeId } from "../../shared/types/domain";

export type GmProviderId = "ollama" | "custom-openai-compatible" | "mock";
export type GmStyleId = "balanced" | "creative" | "strict";
export type GmResponseLengthId = "short" | "normal" | "epic";
export type CanonStrictnessId = "loose" | "normal" | "strict";
export type ThemeModeId = "aelunor-dark" | "high-contrast" | "system";
export type LocationThemeModeId = "automatic" | "fixed";
export type FixedLocationThemeId = "default" | "tavern" | "forest" | "frostlands" | "dungeon" | "city" | "temple";
export type AppearanceUiDensityId = "compact" | "comfortable" | "cinematic";
export type GlowIntensityId = "normal" | "low" | "off";
export type ReadingTextSizeId = "small" | "medium" | "large" | "extra-large";
export type StoryLineHeightId = "normal" | "comfortable" | "spacious";
export type TurnModeId = "story-first" | "balanced" | "rules-aware";
export type RandomnessId = "low" | "normal" | "high";
export type AutoSummaryTurns = 0 | 10 | 20 | 30;
export type UiDensityId = "compact" | "standard" | "comfortable";
export type StoryWidthId = "focused" | "standard" | "wide";
export type TimelineDetailDefault = "collapsed" | "expanded";
export type ComposerModePreference = "do" | "say" | "story";
export type TooltipIntensity = "reduced" | "standard" | "enhanced";
export type LanguageId = "de" | "en";
export type TimeFormatId = "24h" | "12h";
export type DateFormatId = "locale" | "dmy" | "mdy" | "ymd";
export type NumberFormatId = "locale" | "de" | "en";

export interface GmSettings {
  provider: GmProviderId;
  ollamaBaseUrl: string;
  model: string | null;
  style: GmStyleId;
  responseLength: GmResponseLengthId;
  canonStrictness: CanonStrictnessId;
}

export interface AppearanceSettings {
  themeMode: ThemeModeId;
  locationThemeMode: LocationThemeModeId;
  fixedLocationTheme: FixedLocationThemeId;
  uiDensity: AppearanceUiDensityId;
  glowIntensity: GlowIntensityId;
  reducedMotion: boolean;
  // Legacy v1 fields kept during the settings migration slice.
  theme: ThemeId;
  font_preset: FontPresetId;
  font_size: FontSizeId;
  density: UiDensityId;
  story_width: StoryWidthId;
}

export interface ReadingSettings {
  fontPreset: FontPresetId;
  textSize: ReadingTextSizeId;
  storyLineHeight: StoryLineHeightId;
}

export interface GameplaySettings {
  turnMode: TurnModeId;
  randomness: RandomnessId;
  showHints: boolean;
  autoSummaryTurns: AutoSummaryTurns;
}

export interface PrivacySettings {
  preferLocalModels: boolean;
  allowExternalApiCalls: boolean;
  anonymizeDiagnostics: boolean;
}

export interface DiagnosticsSettings {
  showDeveloperPanel: boolean;
}

export interface InteractionSettings {
  auto_scroll: boolean;
  confirm_leave: boolean;
  remember_filters: boolean;
  timeline_detail_default: TimelineDetailDefault;
  shortcuts_enabled: boolean;
  shortcut_hints: boolean;
  composer_mode_preference: ComposerModePreference;
  tooltip_intensity: TooltipIntensity;
}

export interface AccessibilitySettings {
  reduced_motion: boolean;
  high_contrast: boolean;
  strong_focus: boolean;
  larger_targets: boolean;
  reading_friendly_mode: boolean;
}

export interface LocaleSettings {
  language: LanguageId;
  time_format: TimeFormatId;
  date_format: DateFormatId;
  number_format: NumberFormatId;
}

export interface NotificationSettings {
  ui_sound: boolean;
  sound_volume: number;
  desktop_notifications: boolean;
}

export interface LocalDataMetaSettings {
  resettable_local_names: boolean;
  resettable_drafts: boolean;
  resettable_filters: boolean;
}

export interface SettingsMeta {
  schema_version: number;
}

export interface UserSettings {
  gm: GmSettings;
  appearance: AppearanceSettings;
  reading: ReadingSettings;
  gameplay: GameplaySettings;
  privacy: PrivacySettings;
  diagnostics: DiagnosticsSettings;
  interaction: InteractionSettings;
  accessibility: AccessibilitySettings;
  locale: LocaleSettings;
  notifications: NotificationSettings;
  local_data_meta: LocalDataMetaSettings;
  meta: SettingsMeta;
}

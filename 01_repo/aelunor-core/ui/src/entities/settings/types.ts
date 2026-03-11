import type { FontPresetId, FontSizeId, ThemeId } from "../../shared/types/domain";

export type UiDensityId = "compact" | "standard" | "comfortable";
export type StoryWidthId = "focused" | "standard" | "wide";
export type TimelineDetailDefault = "collapsed" | "expanded";
export type ComposerModePreference = "do" | "say" | "story";
export type TooltipIntensity = "reduced" | "standard" | "enhanced";
export type LanguageId = "de" | "en";
export type TimeFormatId = "24h" | "12h";
export type DateFormatId = "locale" | "dmy" | "mdy" | "ymd";
export type NumberFormatId = "locale" | "de" | "en";

export interface AppearanceSettings {
  theme: ThemeId;
  font_preset: FontPresetId;
  font_size: FontSizeId;
  density: UiDensityId;
  story_width: StoryWidthId;
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
  appearance: AppearanceSettings;
  interaction: InteractionSettings;
  accessibility: AccessibilitySettings;
  locale: LocaleSettings;
  notifications: NotificationSettings;
  local_data_meta: LocalDataMetaSettings;
  meta: SettingsMeta;
}

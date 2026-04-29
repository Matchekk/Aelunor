import type { FontPresetId, FontSizeId, ThemeId } from "../../shared/types/domain";
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

export const USER_SETTINGS_SCHEMA_VERSION = 1;

const THEME_IDS: ThemeId[] = ["arcane", "tavern", "glade", "hybrid"];
const FONT_PRESET_IDS: FontPresetId[] = ["classic", "clean", "literary"];
const FONT_SIZE_IDS: FontSizeId[] = ["small", "medium", "large"];
const DENSITY_IDS: UiDensityId[] = ["compact", "standard", "comfortable"];
const STORY_WIDTH_IDS: StoryWidthId[] = ["focused", "standard", "wide"];
const COMPOSER_MODE_PREFERENCE_IDS: ComposerModePreference[] = ["do", "say", "story"];
const TIMELINE_DETAIL_DEFAULT_IDS: TimelineDetailDefault[] = ["collapsed", "expanded"];
const TOOLTIP_INTENSITY_IDS: TooltipIntensity[] = ["reduced", "standard", "enhanced"];
const LANGUAGE_IDS: LanguageId[] = ["de", "en"];
const TIME_FORMAT_IDS: TimeFormatId[] = ["24h", "12h"];
const DATE_FORMAT_IDS: DateFormatId[] = ["locale", "dmy", "mdy", "ymd"];
const NUMBER_FORMAT_IDS: NumberFormatId[] = ["locale", "de", "en"];

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function readBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  return fallback;
}

function readNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return fallback;
}

function readEnum<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  const normalized = readString(value);
  return allowed.includes(normalized as T) ? (normalized as T) : fallback;
}

function normalizeVolume(value: unknown, fallback: number): number {
  const numeric = readNumber(value, fallback);
  return Math.min(100, Math.max(0, Math.round(numeric)));
}

export function resolveSettingsDefaults(): UserSettings {
  const appearance: AppearanceSettings = {
    theme: "hybrid",
    font_preset: "classic",
    font_size: "medium",
    density: "standard",
    story_width: "standard",
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
    appearance,
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

export function normalizeSettings(raw: unknown, fallback = resolveSettingsDefaults()): UserSettings {
  const record = readRecord(raw);
  const appearance = readRecord(record.appearance);
  const interaction = readRecord(record.interaction);
  const accessibility = readRecord(record.accessibility);
  const locale = readRecord(record.locale);
  const notifications = readRecord(record.notifications);
  const localDataMeta = readRecord(record.local_data_meta);

  return {
    appearance: {
      theme: readEnum(appearance.theme, THEME_IDS, fallback.appearance.theme),
      font_preset: readEnum(appearance.font_preset, FONT_PRESET_IDS, fallback.appearance.font_preset),
      font_size: readEnum(appearance.font_size, FONT_SIZE_IDS, fallback.appearance.font_size),
      density: readEnum(appearance.density, DENSITY_IDS, fallback.appearance.density),
      story_width: readEnum(appearance.story_width, STORY_WIDTH_IDS, fallback.appearance.story_width),
    },
    interaction: {
      auto_scroll: readBoolean(interaction.auto_scroll, fallback.interaction.auto_scroll),
      confirm_leave: readBoolean(interaction.confirm_leave, fallback.interaction.confirm_leave),
      remember_filters: readBoolean(interaction.remember_filters, fallback.interaction.remember_filters),
      timeline_detail_default: readEnum(
        interaction.timeline_detail_default,
        TIMELINE_DETAIL_DEFAULT_IDS,
        fallback.interaction.timeline_detail_default,
      ),
      shortcuts_enabled: readBoolean(interaction.shortcuts_enabled, fallback.interaction.shortcuts_enabled),
      shortcut_hints: readBoolean(interaction.shortcut_hints, fallback.interaction.shortcut_hints),
      composer_mode_preference: readEnum(
        interaction.composer_mode_preference,
        COMPOSER_MODE_PREFERENCE_IDS,
        fallback.interaction.composer_mode_preference,
      ),
      tooltip_intensity: readEnum(interaction.tooltip_intensity, TOOLTIP_INTENSITY_IDS, fallback.interaction.tooltip_intensity),
    },
    accessibility: {
      reduced_motion: readBoolean(accessibility.reduced_motion, fallback.accessibility.reduced_motion),
      high_contrast: readBoolean(accessibility.high_contrast, fallback.accessibility.high_contrast),
      strong_focus: readBoolean(accessibility.strong_focus, fallback.accessibility.strong_focus),
      larger_targets: readBoolean(accessibility.larger_targets, fallback.accessibility.larger_targets),
      reading_friendly_mode: readBoolean(accessibility.reading_friendly_mode, fallback.accessibility.reading_friendly_mode),
    },
    locale: {
      language: readEnum(locale.language, LANGUAGE_IDS, fallback.locale.language),
      time_format: readEnum(locale.time_format, TIME_FORMAT_IDS, fallback.locale.time_format),
      date_format: readEnum(locale.date_format, DATE_FORMAT_IDS, fallback.locale.date_format),
      number_format: readEnum(locale.number_format, NUMBER_FORMAT_IDS, fallback.locale.number_format),
    },
    notifications: {
      ui_sound: readBoolean(notifications.ui_sound, fallback.notifications.ui_sound),
      sound_volume: normalizeVolume(notifications.sound_volume, fallback.notifications.sound_volume),
      desktop_notifications: readBoolean(notifications.desktop_notifications, fallback.notifications.desktop_notifications),
    },
    local_data_meta: {
      resettable_local_names: readBoolean(localDataMeta.resettable_local_names, fallback.local_data_meta.resettable_local_names),
      resettable_drafts: readBoolean(localDataMeta.resettable_drafts, fallback.local_data_meta.resettable_drafts),
      resettable_filters: readBoolean(localDataMeta.resettable_filters, fallback.local_data_meta.resettable_filters),
    },
    meta: {
      schema_version: USER_SETTINGS_SCHEMA_VERSION,
    },
  };
}

export function migrateSettings(raw: unknown): UserSettings {
  const record = readRecord(raw);

  if ("settings" in record) {
    return normalizeSettings(readRecord(record.settings));
  }

  return normalizeSettings(record);
}

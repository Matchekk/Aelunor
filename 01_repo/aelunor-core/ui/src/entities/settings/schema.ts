import type { FontPresetId, ThemeId } from "../../shared/types/domain";
import type {
  AppearanceUiDensityId,
  AppearanceSettings,
  AutoSummaryTurns,
  CanonStrictnessId,
  ComposerModePreference,
  DateFormatId,
  FixedLocationThemeId,
  GlowIntensityId,
  GmProviderId,
  GmResponseLengthId,
  GmStyleId,
  LanguageId,
  LocationThemeModeId,
  NumberFormatId,
  RandomnessId,
  ReadingSettings,
  ReadingTextSizeId,
  StoryWidthId,
  StoryLineHeightId,
  ThemeModeId,
  TimeFormatId,
  TimelineDetailDefault,
  TurnModeId,
  TooltipIntensity,
  UiDensityId,
  UserSettings,
} from "./types";
import { fontSizeLabelToPx, fontSizePxToLabel, normalizeFontSizePx } from "./fontSize";
import { resolveSettingsDefaults, USER_SETTINGS_SCHEMA_VERSION } from "./defaults";

export { resolveSettingsDefaults, USER_SETTINGS_SCHEMA_VERSION } from "./defaults";

const THEME_IDS: ThemeId[] = ["arcane", "tavern", "glade", "hybrid"];
const FONT_PRESET_IDS: FontPresetId[] = ["aelunor-classic", "book-mode", "readable", "literary-fantasy", "international"];
const GM_PROVIDER_IDS: GmProviderId[] = ["ollama", "custom-openai-compatible", "mock"];
const GM_STYLE_IDS: GmStyleId[] = ["balanced", "creative", "strict"];
const GM_RESPONSE_LENGTH_IDS: GmResponseLengthId[] = ["short", "normal", "epic"];
const CANON_STRICTNESS_IDS: CanonStrictnessId[] = ["loose", "normal", "strict"];
const THEME_MODE_IDS: ThemeModeId[] = ["aelunor-dark", "high-contrast", "system"];
const LOCATION_THEME_MODE_IDS: LocationThemeModeId[] = ["automatic", "fixed"];
const FIXED_LOCATION_THEME_IDS: FixedLocationThemeId[] = ["default", "tavern", "forest", "frostlands", "dungeon", "city", "temple"];
const APPEARANCE_UI_DENSITY_IDS: AppearanceUiDensityId[] = ["compact", "comfortable", "cinematic"];
const GLOW_INTENSITY_IDS: GlowIntensityId[] = ["normal", "low", "off"];
const READING_TEXT_SIZE_IDS: ReadingTextSizeId[] = ["small", "medium", "large", "extra-large"];
const STORY_LINE_HEIGHT_IDS: StoryLineHeightId[] = ["normal", "comfortable", "spacious"];
const TURN_MODE_IDS: TurnModeId[] = ["story-first", "balanced", "rules-aware"];
const RANDOMNESS_IDS: RandomnessId[] = ["low", "normal", "high"];
const AUTO_SUMMARY_TURNS_IDS: AutoSummaryTurns[] = [0, 10, 20, 30];
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

function readNumberEnum<T extends number>(value: unknown, allowed: readonly T[], fallback: T): T {
  const numeric = readNumber(value, fallback);
  return allowed.includes(numeric as T) ? (numeric as T) : fallback;
}

function readNullableString(value: unknown, fallback: string | null): string | null {
  if (value === null) {
    return null;
  }
  const normalized = readString(value).trim();
  return normalized ? normalized : fallback;
}

function readFontPreset(value: unknown, fallback: FontPresetId): FontPresetId {
  const normalized = readString(value);
  if (FONT_PRESET_IDS.includes(normalized as FontPresetId)) {
    return normalized as FontPresetId;
  }
  if (normalized === "classic") {
    return "aelunor-classic";
  }
  if (normalized === "clean") {
    return "readable";
  }
  if (normalized === "literary") {
    return "literary-fantasy";
  }
  return fallback;
}

function normalizeVolume(value: unknown, fallback: number): number {
  const numeric = readNumber(value, fallback);
  return Math.min(100, Math.max(0, Math.round(numeric)));
}

function readTextSize(value: unknown, fallback: ReadingTextSizeId): ReadingTextSizeId {
  const normalized = readString(value);
  if (READING_TEXT_SIZE_IDS.includes(normalized as ReadingTextSizeId)) {
    return normalized as ReadingTextSizeId;
  }
  return fontSizePxToLabel(value || fontSizeLabelToPx(fallback));
}

function legacyThemeFromMode(themeMode: ThemeModeId): ThemeId {
  return themeMode === "high-contrast" ? "arcane" : "hybrid";
}

function legacyDensityFromUiDensity(uiDensity: AppearanceUiDensityId): UiDensityId {
  return uiDensity === "compact" ? "compact" : "comfortable";
}

export function normalizeSettings(raw: unknown, fallback = resolveSettingsDefaults()): UserSettings {
  const record = readRecord(raw);
  const gm = readRecord(record.gm);
  const appearance = readRecord(record.appearance);
  const reading = readRecord(record.reading);
  const gameplay = readRecord(record.gameplay);
  const privacy = readRecord(record.privacy);
  const diagnostics = readRecord(record.diagnostics);
  const interaction = readRecord(record.interaction);
  const accessibility = readRecord(record.accessibility);
  const locale = readRecord(record.locale);
  const notifications = readRecord(record.notifications);
  const localDataMeta = readRecord(record.local_data_meta);
  const normalizedReading: ReadingSettings = {
    fontPreset: readFontPreset(reading.fontPreset ?? appearance.font_preset, fallback.reading.fontPreset),
    textSize: readTextSize(reading.textSize ?? appearance.font_size, fallback.reading.textSize),
    storyLineHeight: readEnum(reading.storyLineHeight, STORY_LINE_HEIGHT_IDS, fallback.reading.storyLineHeight),
  };
  const normalizedAppearance: AppearanceSettings = {
    themeMode: readEnum(appearance.themeMode, THEME_MODE_IDS, fallback.appearance.themeMode),
    locationThemeMode: readEnum(appearance.locationThemeMode, LOCATION_THEME_MODE_IDS, fallback.appearance.locationThemeMode),
    fixedLocationTheme: readEnum(appearance.fixedLocationTheme, FIXED_LOCATION_THEME_IDS, fallback.appearance.fixedLocationTheme),
    uiDensity: readEnum(appearance.uiDensity ?? appearance.density, APPEARANCE_UI_DENSITY_IDS, fallback.appearance.uiDensity),
    glowIntensity: readEnum(appearance.glowIntensity, GLOW_INTENSITY_IDS, fallback.appearance.glowIntensity),
    reducedMotion: readBoolean(appearance.reducedMotion ?? accessibility.reduced_motion, fallback.appearance.reducedMotion),
    theme: readEnum(appearance.theme, THEME_IDS, legacyThemeFromMode(fallback.appearance.themeMode)),
    font_preset: normalizedReading.fontPreset,
    font_size: normalizeFontSizePx(appearance.font_size, fontSizeLabelToPx(normalizedReading.textSize)),
    density: readEnum(appearance.density, DENSITY_IDS, legacyDensityFromUiDensity(fallback.appearance.uiDensity)),
    story_width: readEnum(appearance.story_width, STORY_WIDTH_IDS, fallback.appearance.story_width),
  };

  return {
    gm: {
      provider: readEnum(gm.provider, GM_PROVIDER_IDS, fallback.gm.provider),
      ollamaBaseUrl: readString(gm.ollamaBaseUrl).trim() || fallback.gm.ollamaBaseUrl,
      model: readNullableString(gm.model, fallback.gm.model),
      style: readEnum(gm.style, GM_STYLE_IDS, fallback.gm.style),
      responseLength: readEnum(gm.responseLength, GM_RESPONSE_LENGTH_IDS, fallback.gm.responseLength),
      canonStrictness: readEnum(gm.canonStrictness, CANON_STRICTNESS_IDS, fallback.gm.canonStrictness),
    },
    appearance: normalizedAppearance,
    reading: normalizedReading,
    gameplay: {
      turnMode: readEnum(gameplay.turnMode, TURN_MODE_IDS, fallback.gameplay.turnMode),
      randomness: readEnum(gameplay.randomness, RANDOMNESS_IDS, fallback.gameplay.randomness),
      showHints: readBoolean(gameplay.showHints, fallback.gameplay.showHints),
      autoSummaryTurns: readNumberEnum(gameplay.autoSummaryTurns, AUTO_SUMMARY_TURNS_IDS, fallback.gameplay.autoSummaryTurns),
    },
    privacy: {
      preferLocalModels: readBoolean(privacy.preferLocalModels, fallback.privacy.preferLocalModels),
      allowExternalApiCalls: readBoolean(privacy.allowExternalApiCalls, fallback.privacy.allowExternalApiCalls),
      anonymizeDiagnostics: readBoolean(privacy.anonymizeDiagnostics, fallback.privacy.anonymizeDiagnostics),
    },
    diagnostics: {
      showDeveloperPanel: readBoolean(diagnostics.showDeveloperPanel, fallback.diagnostics.showDeveloperPanel),
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
      reduced_motion: normalizedAppearance.reducedMotion,
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

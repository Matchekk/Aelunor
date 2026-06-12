import { describe, expect, it } from "vitest";

import { migrateSettings, normalizeSettings, resolveSettingsDefaults, USER_SETTINGS_SCHEMA_VERSION } from "./schema";

describe("settings schema", () => {
  it("returns a complete default schema", () => {
    const defaults = resolveSettingsDefaults();

    expect(defaults.meta.schema_version).toBe(USER_SETTINGS_SCHEMA_VERSION);
    expect(defaults.appearance.theme).toBe("hybrid");
    expect(defaults.gm.provider).toBe("ollama");
    expect(defaults.gm.ollamaBaseUrl).toBe("http://127.0.0.1:11434");
    expect(defaults.gm.model).toBeNull();
    expect(defaults.gm.style).toBe("balanced");
    expect(defaults.gm.responseLength).toBe("normal");
    expect(defaults.gm.canonStrictness).toBe("normal");
    expect(defaults.appearance.themeMode).toBe("aelunor-dark");
    expect(defaults.appearance.locationThemeMode).toBe("automatic");
    expect(defaults.appearance.fixedLocationTheme).toBe("default");
    expect(defaults.appearance.uiDensity).toBe("comfortable");
    expect(defaults.appearance.glowIntensity).toBe("normal");
    expect(defaults.appearance.reducedMotion).toBe(false);
    expect(defaults.appearance.font_preset).toBe("aelunor-classic");
    expect(defaults.appearance.font_size).toBe(16);
    expect(defaults.reading.fontPreset).toBe("aelunor-classic");
    expect(defaults.reading.textSize).toBe("medium");
    expect(defaults.reading.storyLineHeight).toBe("comfortable");
    expect(defaults.gameplay.turnMode).toBe("balanced");
    expect(defaults.gameplay.randomness).toBe("normal");
    expect(defaults.gameplay.showHints).toBe(true);
    expect(defaults.gameplay.autoSummaryTurns).toBe(20);
    expect(defaults.privacy.preferLocalModels).toBe(true);
    expect(defaults.privacy.allowExternalApiCalls).toBe(false);
    expect(defaults.privacy.anonymizeDiagnostics).toBe(true);
    expect(defaults.diagnostics.showDeveloperPanel).toBe(false);
    expect(defaults.interaction.timeline_detail_default).toBe("collapsed");
    expect(defaults.accessibility.reduced_motion).toBe(false);
    expect(defaults.locale.language).toBe("de");
    expect(defaults.notifications.sound_volume).toBe(60);
  });

  it("normalizes invalid values back to defaults", () => {
    const normalized = normalizeSettings({
      appearance: {
        theme: "invalid-theme",
      },
      interaction: {
        auto_scroll: "yes",
        timeline_detail_default: "open",
      },
      notifications: {
        sound_volume: 999,
      },
      locale: {
        language: "xx",
      },
      gm: {
        provider: "cloud",
        ollamaBaseUrl: " ",
        model: "",
        style: "wild",
        responseLength: "novel",
        canonStrictness: "lawful",
      },
      reading: {
        textSize: "huge",
        storyLineHeight: "tight",
      },
      gameplay: {
        turnMode: "combat-only",
        randomness: "chaos",
        showHints: "yes",
        autoSummaryTurns: 999,
      },
    });

    expect(normalized.appearance.theme).toBe("hybrid");
    expect(normalized.gm.provider).toBe("ollama");
    expect(normalized.gm.ollamaBaseUrl).toBe("http://127.0.0.1:11434");
    expect(normalized.gm.model).toBeNull();
    expect(normalized.gm.style).toBe("balanced");
    expect(normalized.reading.textSize).toBe("medium");
    expect(normalized.reading.storyLineHeight).toBe("comfortable");
    expect(normalized.gameplay.turnMode).toBe("balanced");
    expect(normalized.gameplay.randomness).toBe("normal");
    expect(normalized.gameplay.autoSummaryTurns).toBe(20);
    expect(normalized.interaction.auto_scroll).toBe(true);
    expect(normalized.interaction.timeline_detail_default).toBe("collapsed");
    expect(normalized.notifications.sound_volume).toBe(100);
    expect(normalized.locale.language).toBe("de");
    expect(normalized.meta.schema_version).toBe(USER_SETTINGS_SCHEMA_VERSION);
  });

  it("migrates wrapped persisted payloads", () => {
    const migrated = migrateSettings({
      settings: {
        appearance: {
          theme: "hybrid",
          font_preset: "book-mode",
          font_size: 19,
          density: "compact",
          story_width: "focused",
          uiDensity: "cinematic",
        },
        gm: {
          provider: "ollama",
          ollamaBaseUrl: "http://localhost:11434/",
          model: "llama3.1:8b",
        },
        reading: {
          fontPreset: "readable",
          textSize: "large",
          storyLineHeight: "spacious",
        },
      },
    });

    expect(migrated.gm.model).toBe("llama3.1:8b");
    expect(migrated.gm.ollamaBaseUrl).toBe("http://localhost:11434/");
    expect(migrated.appearance.theme).toBe("hybrid");
    expect(migrated.reading.fontPreset).toBe("readable");
    expect(migrated.reading.textSize).toBe("large");
    expect(migrated.reading.storyLineHeight).toBe("spacious");
    expect(migrated.appearance.font_preset).toBe("readable");
    expect(migrated.appearance.font_size).toBe(19);
    expect(migrated.appearance.density).toBe("compact");
    expect(migrated.appearance.uiDensity).toBe("cinematic");
    expect(migrated.appearance.story_width).toBe("focused");
    expect(migrated.meta.schema_version).toBe(USER_SETTINGS_SCHEMA_VERSION);
  });

  it("maps old font preset values to the new preset ids", () => {
    expect(normalizeSettings({ appearance: { font_preset: "classic" } }).appearance.font_preset).toBe("aelunor-classic");
    expect(normalizeSettings({ appearance: { font_preset: "clean" } }).appearance.font_preset).toBe("readable");
    expect(normalizeSettings({ appearance: { font_preset: "literary" } }).appearance.font_preset).toBe("literary-fantasy");
  });

  it("normalizes font size values and migrates old labels", () => {
    expect(normalizeSettings({ appearance: { font_size: "small" } }).appearance.font_size).toBe(14);
    expect(normalizeSettings({ appearance: { font_size: "medium" } }).appearance.font_size).toBe(16);
    expect(normalizeSettings({ appearance: { font_size: "large" } }).appearance.font_size).toBe(18);
    expect(normalizeSettings({ appearance: { font_size: "20" } }).appearance.font_size).toBe(20);
    expect(normalizeSettings({ appearance: { font_size: 99 } }).appearance.font_size).toBe(20);
    expect(normalizeSettings({ appearance: { font_size: 8 } }).appearance.font_size).toBe(14);
  });
});

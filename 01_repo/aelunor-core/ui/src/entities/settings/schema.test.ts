import { describe, expect, it } from "vitest";

import { migrateSettings, normalizeSettings, resolveSettingsDefaults, USER_SETTINGS_SCHEMA_VERSION } from "./schema";

describe("settings schema", () => {
  it("returns a complete default schema", () => {
    const defaults = resolveSettingsDefaults();

    expect(defaults.meta.schema_version).toBe(USER_SETTINGS_SCHEMA_VERSION);
    expect(defaults.appearance.theme).toBe("arcane");
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
    });

    expect(normalized.appearance.theme).toBe("arcane");
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
          font_preset: "clean",
          font_size: "large",
          density: "compact",
          story_width: "focused",
        },
      },
    });

    expect(migrated.appearance.theme).toBe("hybrid");
    expect(migrated.appearance.font_preset).toBe("clean");
    expect(migrated.appearance.font_size).toBe("large");
    expect(migrated.appearance.density).toBe("compact");
    expect(migrated.appearance.story_width).toBe("focused");
    expect(migrated.meta.schema_version).toBe(USER_SETTINGS_SCHEMA_VERSION);
  });
});

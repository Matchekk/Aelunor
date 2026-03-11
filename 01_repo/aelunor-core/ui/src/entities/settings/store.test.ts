import { describe, expect, it } from "vitest";

import { readLegacyAppearanceFromStorage, resolveInitialSettingsFromStorage } from "./store";

class MemoryStorage implements Storage {
  private map = new Map<string, string>();

  get length(): number {
    return this.map.size;
  }

  clear(): void {
    this.map.clear();
  }

  getItem(key: string): string | null {
    return this.map.has(key) ? this.map.get(key) ?? null : null;
  }

  key(index: number): string | null {
    return Array.from(this.map.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.map.delete(key);
  }

  setItem(key: string, value: string): void {
    this.map.set(key, value);
  }
}

describe("settings store migration helpers", () => {
  it("reads legacy appearance from persisted legacy theme store", () => {
    const storage = new MemoryStorage();
    storage.setItem(
      "isekaiThemeStateV1",
      JSON.stringify({
        state: {
          theme: "hybrid",
          font_preset: "clean",
          font_size: "large",
        },
      }),
    );

    const legacy = readLegacyAppearanceFromStorage(storage);
    expect(legacy.theme).toBe("hybrid");
    expect(legacy.font_preset).toBe("clean");
    expect(legacy.font_size).toBe("large");
  });

  it("falls back to defaults and applies legacy appearance when new schema is missing", () => {
    const storage = new MemoryStorage();
    storage.setItem("isekaiTheme", "glade");
    storage.setItem("isekaiFontPreset", "literary");
    storage.setItem("isekaiFontSize", "small");

    const settings = resolveInitialSettingsFromStorage(storage);
    expect(settings.appearance.theme).toBe("glade");
    expect(settings.appearance.font_preset).toBe("literary");
    expect(settings.appearance.font_size).toBe("small");
    expect(storage.getItem("aelunorUserSettingsV1")).not.toBeNull();
  });

  it("recovers from malformed persisted payloads", () => {
    const storage = new MemoryStorage();
    storage.setItem("aelunorUserSettingsV1", "{");

    const settings = resolveInitialSettingsFromStorage(storage);
    expect(settings.appearance.theme).toBe("arcane");
    expect(settings.locale.language).toBe("de");
  });
});

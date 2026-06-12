import { afterEach, describe, expect, it, vi } from "vitest";

import { readLegacyAppearanceFromStorage, resolveInitialSettingsFromStorage, useUserSettingsStore } from "./store";

afterEach(() => {
  vi.unstubAllGlobals();
});

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
    expect(legacy.font_preset).toBe("readable");
    expect(legacy.font_size).toBe(18);
  });

  it("falls back to defaults and applies legacy appearance when new schema is missing", () => {
    const storage = new MemoryStorage();
    storage.setItem("isekaiTheme", "glade");
    storage.setItem("isekaiFontPreset", "literary");
    storage.setItem("isekaiFontSize", "small");

    const settings = resolveInitialSettingsFromStorage(storage);
    expect(settings.appearance.theme).toBe("glade");
    expect(settings.appearance.font_preset).toBe("literary-fantasy");
    expect(settings.appearance.font_size).toBe(14);
    expect(storage.getItem("aelunorUserSettingsV1")).not.toBeNull();
    expect(storage.getItem("isekaiFontSize")).toBe("14");
  });

  it("recovers from malformed persisted payloads", () => {
    const storage = new MemoryStorage();
    storage.setItem("aelunorUserSettingsV1", "{");

    const settings = resolveInitialSettingsFromStorage(storage);
    expect(settings.appearance.theme).toBe("hybrid");
    expect(settings.appearance.font_preset).toBe("aelunor-classic");
    expect(settings.appearance.font_size).toBe(16);
    expect(settings.locale.language).toBe("de");
  });

  it("persists the selected GM model and reloads it", () => {
    const storage = new MemoryStorage();
    vi.stubGlobal("window", { localStorage: storage });

    useUserSettingsStore.getState().patch_gm({
      ollamaBaseUrl: "http://127.0.0.1:11434",
      model: "llama3.1:8b",
    });

    const persisted = storage.getItem("aelunorUserSettingsV1");
    expect(persisted).not.toBeNull();
    const reloaded = resolveInitialSettingsFromStorage(storage);
    expect(reloaded.gm.model).toBe("llama3.1:8b");
    expect(reloaded.gm.ollamaBaseUrl).toBe("http://127.0.0.1:11434");
  });
});

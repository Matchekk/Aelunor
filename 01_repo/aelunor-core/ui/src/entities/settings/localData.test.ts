import { describe, expect, it } from "vitest";

import { clearLocalComfortDataFromStorages } from "./localData";

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

describe("clearLocalComfortDataFromStorages", () => {
  it("clears only comfort keys from local and session storage", () => {
    const local = new MemoryStorage();
    const session = new MemoryStorage();

    local.setItem("isekaiSessionLibrary", "1");
    local.setItem("isekaiNoveltyState", "2");
    local.setItem("aelunorPlayUiMemoryV1", "3");
    local.setItem("aelunorSettingsUiMemoryV1", "4");
    local.setItem("isekaiCampaignId", "keep");
    session.setItem("aelunorV1ContextCache", "ctx");
    session.setItem("unrelated", "keep");

    clearLocalComfortDataFromStorages(local, session);

    expect(local.getItem("isekaiSessionLibrary")).toBeNull();
    expect(local.getItem("isekaiNoveltyState")).toBeNull();
    expect(local.getItem("aelunorPlayUiMemoryV1")).toBeNull();
    expect(local.getItem("aelunorSettingsUiMemoryV1")).toBeNull();
    expect(local.getItem("isekaiCampaignId")).toBe("keep");
    expect(session.getItem("aelunorV1ContextCache")).toBeNull();
    expect(session.getItem("unrelated")).toBe("keep");
  });
});

import { describe, expect, it } from "vitest";

import {
  COMPOSER_DEFAULT_HEIGHT,
  COMPOSER_HEIGHT_STORAGE_KEY,
  COMPOSER_MIN_HEIGHT,
  clampComposerHeight,
  deriveMaxComposerHeight,
  readStoredComposerHeight,
  writeStoredComposerHeight,
} from "./composerResize";

describe("deriveMaxComposerHeight", () => {
  it("caps the composer at 44% of the available center height", () => {
    expect(deriveMaxComposerHeight(1000)).toBe(440);
  });

  it("keeps the journal minimum on small viewports", () => {
    // 600px available: 44% = 264, journal guard = 600 - 260 - 12 = 328 -> ratio wins
    expect(deriveMaxComposerHeight(600)).toBe(264);
    // 500px available: 44% = 220, journal guard = 228 -> ratio wins, floor at min
    expect(deriveMaxComposerHeight(500)).toBe(COMPOSER_MIN_HEIGHT);
  });

  it("never returns less than the composer minimum", () => {
    expect(deriveMaxComposerHeight(100)).toBe(COMPOSER_MIN_HEIGHT);
    expect(deriveMaxComposerHeight(0)).toBe(COMPOSER_DEFAULT_HEIGHT);
    expect(deriveMaxComposerHeight(Number.NaN)).toBe(COMPOSER_DEFAULT_HEIGHT);
  });
});

describe("clampComposerHeight", () => {
  it("clamps too-small values to the minimum", () => {
    expect(clampComposerHeight(50, 1000)).toBe(COMPOSER_MIN_HEIGHT);
    expect(clampComposerHeight(-400, 1000)).toBe(COMPOSER_MIN_HEIGHT);
  });

  it("clamps too-large values to the maximum", () => {
    expect(clampComposerHeight(2000, 1000)).toBe(440);
  });

  it("clamps a legacy 55%-era stored value down to the new 44% cap", () => {
    // 450px stored under the old rules, center height ~958px at 1920x1080
    expect(clampComposerHeight(450, 958)).toBe(422);
  });

  it("uses a default that fits all composer controls without scrolling", () => {
    expect(COMPOSER_DEFAULT_HEIGHT).toBe(340);
    expect(clampComposerHeight(undefined, 1000)).toBe(340);
  });

  it("falls back to the default for invalid values", () => {
    expect(clampComposerHeight("kaputt", 1000)).toBe(COMPOSER_DEFAULT_HEIGHT);
    expect(clampComposerHeight(null, 1000)).toBe(COMPOSER_DEFAULT_HEIGHT);
    expect(clampComposerHeight(undefined, 1000)).toBe(COMPOSER_DEFAULT_HEIGHT);
    expect(clampComposerHeight(Number.NaN, 1000)).toBe(COMPOSER_DEFAULT_HEIGHT);
  });

  it("keeps valid values and rounds them", () => {
    expect(clampComposerHeight(312.6, 1000)).toBe(313);
  });
});

describe("stored composer height", () => {
  function memoryStorage(initial: Record<string, string> = {}): Pick<Storage, "getItem" | "setItem"> & { data: Record<string, string> } {
    const data = { ...initial };
    return {
      data,
      getItem: (key: string) => (key in data ? data[key]! : null),
      setItem: (key: string, value: string) => {
        data[key] = value;
      },
    };
  }

  it("round-trips the height through the v1 storage key", () => {
    const storage = memoryStorage();
    writeStoredComposerHeight(storage, 342.4);
    expect(storage.data[COMPOSER_HEIGHT_STORAGE_KEY]).toBe("342");
    expect(readStoredComposerHeight(storage)).toBe(342);
  });

  it("returns null for missing or broken stored values", () => {
    expect(readStoredComposerHeight(memoryStorage())).toBeNull();
    expect(readStoredComposerHeight(memoryStorage({ [COMPOSER_HEIGHT_STORAGE_KEY]: "abc" }))).toBeNull();
    expect(readStoredComposerHeight(null)).toBeNull();
  });

  it("survives a throwing storage", () => {
    const throwing = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(readStoredComposerHeight(throwing)).toBeNull();
    expect(() => writeStoredComposerHeight(throwing, 300)).not.toThrow();
  });
});

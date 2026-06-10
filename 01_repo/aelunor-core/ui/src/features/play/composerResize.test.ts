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
  it("caps the composer at 55% of the available center height", () => {
    expect(deriveMaxComposerHeight(1000)).toBe(550);
  });

  it("keeps the journal minimum on small viewports", () => {
    // 600px available: 55% = 330, journal guard = 600 - 220 - 12 = 368 -> 330 wins
    expect(deriveMaxComposerHeight(600)).toBe(330);
    // 500px available: journal guard = 268, 55% = 275 -> guard wins
    expect(deriveMaxComposerHeight(500)).toBe(268);
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
    expect(clampComposerHeight(2000, 1000)).toBe(550);
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

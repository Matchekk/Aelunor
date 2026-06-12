export const FONT_SIZE_MIN_PX = 14;
export const FONT_SIZE_DEFAULT_PX = 16;
export const FONT_SIZE_MAX_PX = 20;
export const FONT_SIZE_STEP_PX = 1;

const LEGACY_FONT_SIZE_PX: Record<string, number> = {
  small: 14,
  medium: 16,
  large: 18,
};

export function clampFontSizePx(value: number): number {
  return Math.min(FONT_SIZE_MAX_PX, Math.max(FONT_SIZE_MIN_PX, Math.round(value)));
}

export function normalizeFontSizePx(value: unknown, fallback = FONT_SIZE_DEFAULT_PX): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return clampFontSizePx(value);
  }

  if (typeof value === "string") {
    const legacyValue = LEGACY_FONT_SIZE_PX[value];
    if (legacyValue !== undefined) {
      return legacyValue;
    }

    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return clampFontSizePx(parsed);
    }
  }

  return clampFontSizePx(fallback);
}

export function readFontSizePx(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return clampFontSizePx(value);
  }

  if (typeof value === "string" && (value in LEGACY_FONT_SIZE_PX || Number.isFinite(Number(value)))) {
    return normalizeFontSizePx(value);
  }

  return null;
}

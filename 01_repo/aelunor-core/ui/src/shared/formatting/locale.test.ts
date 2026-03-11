import { describe, expect, it } from "vitest";

import type { LocaleSettings } from "../../entities/settings/types";
import { formatDate, formatDateTime, formatNumber, formatTime } from "./locale";

const DE_BASE: LocaleSettings = {
  language: "de",
  time_format: "24h",
  date_format: "locale",
  number_format: "locale",
};

describe("locale formatting", () => {
  it("returns null for invalid datetime values", () => {
    expect(formatDateTime("not-a-date", DE_BASE)).toBeNull();
    expect(formatDate("not-a-date", DE_BASE)).toBeNull();
    expect(formatTime("not-a-date", DE_BASE)).toBeNull();
  });

  it("changes output when date/time formats change", () => {
    const date = "2025-03-11T13:05:00.000Z";

    const time24 = formatTime(date, { ...DE_BASE, language: "en", time_format: "24h" });
    const time12 = formatTime(date, { ...DE_BASE, language: "en", time_format: "12h" });
    const dateDmy = formatDate(date, { ...DE_BASE, date_format: "dmy" });
    const dateMdy = formatDate(date, { ...DE_BASE, language: "en", date_format: "mdy" });

    expect(time24).not.toBeNull();
    expect(time12).not.toBeNull();
    expect(time24).not.toEqual(time12);
    expect(dateDmy).not.toBeNull();
    expect(dateMdy).not.toBeNull();
    expect(dateDmy).not.toEqual(dateMdy);
  });

  it("formats numbers based on number format preference", () => {
    const de = formatNumber(12345.67, { ...DE_BASE, number_format: "de" });
    const en = formatNumber(12345.67, { ...DE_BASE, number_format: "en", language: "en" });
    expect(de).not.toEqual(en);
  });
});

import { resolveSettingsDefaults } from "../../entities/settings/schema";
import { useUserSettingsStore } from "../../entities/settings/store";
import type { DateFormatId, LocaleSettings, NumberFormatId, TimeFormatId } from "../../entities/settings/types";

function readLocaleSettings(): LocaleSettings {
  const state = useUserSettingsStore.getState();
  return state.locale ?? resolveSettingsDefaults().locale;
}

function resolveLocaleTag(language: LocaleSettings["language"]): string {
  return language === "en" ? "en-US" : "de-DE";
}

function localeTagForNumber(locale: LocaleSettings): string {
  const mapping: Record<NumberFormatId, string> = {
    locale: resolveLocaleTag(locale.language),
    de: "de-DE",
    en: "en-US",
  };
  return mapping[locale.number_format];
}

function dateOptionsByFormat(date_format: DateFormatId): Intl.DateTimeFormatOptions {
  if (date_format === "dmy") {
    return { day: "2-digit", month: "2-digit", year: "numeric" };
  }
  if (date_format === "mdy") {
    return { month: "2-digit", day: "2-digit", year: "numeric" };
  }
  if (date_format === "ymd") {
    return { year: "numeric", month: "2-digit", day: "2-digit" };
  }
  return { dateStyle: "medium" };
}

function timeOptionsByFormat(time_format: TimeFormatId): Intl.DateTimeFormatOptions {
  return time_format === "12h"
    ? { hour: "2-digit", minute: "2-digit", hour12: true }
    : { hour: "2-digit", minute: "2-digit", hour12: false };
}

function toDate(value: string | number | Date): Date | null {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isFinite(date.getTime()) ? date : null;
}

export function formatDateTime(value: string | number | Date, locale_override: LocaleSettings | null = null): string | null {
  const date = toDate(value);
  if (!date) {
    return null;
  }
  const locale = locale_override ?? readLocaleSettings();
  const locale_tag = resolveLocaleTag(locale.language);
  const datePart = new Intl.DateTimeFormat(locale_tag, dateOptionsByFormat(locale.date_format)).format(date);
  const timePart = new Intl.DateTimeFormat(locale_tag, timeOptionsByFormat(locale.time_format)).format(date);
  return `${datePart}, ${timePart}`;
}

export function formatDate(value: string | number | Date, locale_override: LocaleSettings | null = null): string | null {
  const date = toDate(value);
  if (!date) {
    return null;
  }
  const locale = locale_override ?? readLocaleSettings();
  return new Intl.DateTimeFormat(resolveLocaleTag(locale.language), dateOptionsByFormat(locale.date_format)).format(date);
}

export function formatTime(value: string | number | Date, locale_override: LocaleSettings | null = null): string | null {
  const date = toDate(value);
  if (!date) {
    return null;
  }
  const locale = locale_override ?? readLocaleSettings();
  return new Intl.DateTimeFormat(resolveLocaleTag(locale.language), timeOptionsByFormat(locale.time_format)).format(date);
}

export function formatNumber(value: number, locale_override: LocaleSettings | null = null): string {
  const locale = locale_override ?? readLocaleSettings();
  return new Intl.NumberFormat(localeTagForNumber(locale)).format(value);
}

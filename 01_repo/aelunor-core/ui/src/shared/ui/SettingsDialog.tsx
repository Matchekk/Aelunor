import { useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";

import type {
  ComposerModePreference,
  DateFormatId,
  LanguageId,
  NumberFormatId,
  StoryWidthId,
  TimeFormatId,
  TimelineDetailDefault,
  TooltipIntensity,
  UiDensityId,
} from "../../entities/settings/types";
import type { FontPresetId, FontSizeId, ThemeId } from "../types/domain";
import { useUserSettingsStore } from "../../entities/settings/store";
import { useSurfaceLayer } from "./useSurfaceLayer";
import {
  SettingsField,
  SettingsSection,
  SettingsSegmented,
  SettingsSelect,
  SettingsToggle,
} from "./settings/SettingsFields";

interface SettingsDialogProps {
  open: boolean;
  on_close: () => void;
  return_focus_element?: HTMLElement | null;
}

type SettingsCategory = "appearance" | "interaction" | "accessibility" | "locale" | "data";

const SETTINGS_UI_MEMORY_KEY = "aelunorSettingsUiMemoryV1";

const THEME_OPTIONS: Array<{
  id: ThemeId;
  label: string;
  description: string;
  preview_title: string;
  preview_mode: string;
  swatches: [string, string, string];
}> = [
  {
    id: "arcane",
    label: "Nachtblau",
    description: "Der kühle klare GM-Look.",
    preview_title: "Geschichtsfluss",
    preview_mode: "Story",
    swatches: ["#0f1520", "#1b2a3d", "#7bcaff"],
  },
  {
    id: "tavern",
    label: "Taverne",
    description: "Warmes Holz, Messing und Kerzenlicht.",
    preview_title: "Abend am Kamin",
    preview_mode: "Tun",
    swatches: ["#1e1510", "#3b291d", "#d99c48"],
  },
  {
    id: "glade",
    label: "Waldlichtung",
    description: "Moosgrün, Nebel und ruhige Wildnis.",
    preview_title: "Spuren im Farn",
    preview_mode: "Sagen",
    swatches: ["#0e1c18", "#1b3a31", "#66d49b"],
  },
  {
    id: "hybrid",
    label: "Aelunor (Hybrid)",
    description: "Mittelalter trifft Tech-Magie mit klarem Kontrast.",
    preview_title: "Relikt-Schnittstelle",
    preview_mode: "Tun",
    swatches: ["#111923", "#2d2a39", "#86d2cb"],
  },
];

const FONT_OPTIONS: Array<{ id: FontPresetId; label: string; sample_font: string }> = [
  {
    id: "classic",
    label: "Classic",
    sample_font: '"Palatino Linotype", "Book Antiqua", Palatino, serif',
  },
  {
    id: "clean",
    label: "Clean",
    sample_font: '"Segoe UI", "Trebuchet MS", Tahoma, sans-serif',
  },
  {
    id: "literary",
    label: "Literary",
    sample_font: '"Garamond", "Times New Roman", serif',
  },
];

const SIZE_OPTIONS: Array<{ id: FontSizeId; label: string; preview_px: number }> = [
  { id: "small", label: "Klein", preview_px: 14 },
  { id: "medium", label: "Mittel", preview_px: 16 },
  { id: "large", label: "Groß", preview_px: 18 },
];

const CATEGORY_ITEMS: Array<{ id: SettingsCategory; label: string; description: string }> = [
  { id: "appearance", label: "Darstellung", description: "Theme, Schrift und Flächenrhythmus" },
  { id: "interaction", label: "Lesen & Bedienung", description: "Timeline- und Composer-Verhalten" },
  { id: "accessibility", label: "Barrierefreiheit", description: "Kontrast, Fokus und Bewegungen" },
  { id: "locale", label: "Sprache & Region", description: "Formatierung für Datum/Zeit/Zahlen" },
  { id: "data", label: "Daten & Zurücksetzen", description: "Lokale Präferenzen verwalten" },
];
const DEFAULT_CATEGORY_META = CATEGORY_ITEMS[0]!;

function readCategoryMemory(): SettingsCategory {
  if (typeof window === "undefined") {
    return DEFAULT_CATEGORY_META.id;
  }
  const raw = window.localStorage.getItem(SETTINGS_UI_MEMORY_KEY);
  return CATEGORY_ITEMS.some((item) => item.id === raw) ? (raw as SettingsCategory) : DEFAULT_CATEGORY_META.id;
}

function persistCategoryMemory(category: SettingsCategory): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(SETTINGS_UI_MEMORY_KEY, category);
}

export function SettingsDialog({ open, on_close, return_focus_element = null }: SettingsDialogProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const [activeCategory, setActiveCategory] = useState<SettingsCategory>(() => readCategoryMemory());

  const appearance = useUserSettingsStore((state) => state.appearance);
  const interaction = useUserSettingsStore((state) => state.interaction);
  const accessibility = useUserSettingsStore((state) => state.accessibility);
  const locale = useUserSettingsStore((state) => state.locale);
  const localDataMeta = useUserSettingsStore((state) => state.local_data_meta);

  const setTheme = useUserSettingsStore((state) => state.set_theme);
  const setFontPreset = useUserSettingsStore((state) => state.set_font_preset);
  const setFontSize = useUserSettingsStore((state) => state.set_font_size);
  const setDensity = useUserSettingsStore((state) => state.set_density);
  const setStoryWidth = useUserSettingsStore((state) => state.set_story_width);
  const setAutoScroll = useUserSettingsStore((state) => state.set_auto_scroll);
  const setConfirmLeave = useUserSettingsStore((state) => state.set_confirm_leave);
  const setRememberFilters = useUserSettingsStore((state) => state.set_remember_filters);
  const setTimelineDetailDefault = useUserSettingsStore((state) => state.set_timeline_detail_default);
  const setShortcutsEnabled = useUserSettingsStore((state) => state.set_shortcuts_enabled);
  const setShortcutHints = useUserSettingsStore((state) => state.set_shortcut_hints);
  const setComposerModePreference = useUserSettingsStore((state) => state.set_composer_mode_preference);
  const setTooltipIntensity = useUserSettingsStore((state) => state.set_tooltip_intensity);
  const setReducedMotion = useUserSettingsStore((state) => state.set_reduced_motion);
  const setHighContrast = useUserSettingsStore((state) => state.set_high_contrast);
  const setStrongFocus = useUserSettingsStore((state) => state.set_strong_focus);
  const setLargerTargets = useUserSettingsStore((state) => state.set_larger_targets);
  const setReadingFriendlyMode = useUserSettingsStore((state) => state.set_reading_friendly_mode);
  const setLanguage = useUserSettingsStore((state) => state.set_language);
  const setTimeFormat = useUserSettingsStore((state) => state.set_time_format);
  const setDateFormat = useUserSettingsStore((state) => state.set_date_format);
  const setNumberFormat = useUserSettingsStore((state) => state.set_number_format);
  const resetSettings = useUserSettingsStore((state) => state.reset_settings);
  const clearLocalComfortData = useUserSettingsStore((state) => state.clear_local_comfort_data);

  useSurfaceLayer({
    open,
    kind: "modal",
    priority: 42,
    container: dialogRef.current,
    return_focus_element,
    on_close,
  });

  const activeCategoryMeta = useMemo(
    () => CATEGORY_ITEMS.find((item) => item.id === activeCategory) ?? DEFAULT_CATEGORY_META,
    [activeCategory],
  );

  if (!open) {
    return null;
  }

  return (
    <div className="settings-dialog-backdrop" role="presentation" onClick={on_close}>
      <section
        ref={dialogRef}
        className="settings-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Einstellungen"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="v1-panel-head">
          <h2 className="settings-dialog-title">
            <img className="settings-dialog-logo" src="/brand/aelunor-icon-512x512.png" alt="" aria-hidden="true" />
            <span>Einstellungen</span>
          </h2>
          <button type="button" className="btn ghost" onClick={on_close}>
            Schließen
          </button>
        </header>

        <p className="settings-category-description">
          Globale Präferenzen für Darstellung, Lesefluss und Bedienung. Kampagnenregeln und Host-Steuerung bleiben außerhalb dieser
          Einstellungen.
        </p>

        <div className="settings-dialog-layout">
          <nav className="settings-subnav" aria-label="Einstellungsbereiche">
            {CATEGORY_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={activeCategory === item.id ? "settings-subnav-item is-active" : "settings-subnav-item"}
                onClick={() => {
                  setActiveCategory(item.id);
                  persistCategoryMemory(item.id);
                }}
              >
                <strong>{item.label}</strong>
                <small>{item.description}</small>
              </button>
            ))}
          </nav>

          <div className="settings-dialog-content">
            <div className="settings-content-stack">
              <header className="settings-category-head">
                <h3>{activeCategoryMeta.label}</h3>
                <p className="status-muted">{activeCategoryMeta.description}</p>
              </header>

              {activeCategory === "appearance" ? (
                <>
                  <SettingsSection title="Theme" description="Farbstil mit Vorschau auswählen.">
                    <div className="settings-theme-grid">
                      {THEME_OPTIONS.map((option) => (
                        <article key={option.id} className={appearance.theme === option.id ? "settings-theme-card is-active" : "settings-theme-card"}>
                          <header className="settings-theme-head">
                            <div>
                              <h4>{option.label}</h4>
                              <p>{option.description}</p>
                            </div>
                            <span className="settings-theme-status">{appearance.theme === option.id ? "Aktiv" : "Verfügbar"}</span>
                          </header>

                          <div
                            className="settings-theme-preview-window"
                            style={
                              {
                                "--preview-base": option.swatches[0],
                                "--preview-mid": option.swatches[1],
                                "--preview-accent": option.swatches[2],
                              } as CSSProperties
                            }
                            aria-hidden="true"
                          >
                            <div className="settings-theme-preview-surface">
                              <div className="settings-theme-preview-top">
                                <span className="settings-theme-preview-chip">Code: AB6LXG</span>
                                <span className="settings-theme-preview-menu">
                                  <span />
                                  <span />
                                  <span />
                                </span>
                              </div>
                              <div className="settings-theme-preview-title">{option.preview_title}</div>
                              <div className="settings-theme-preview-mode">{option.preview_mode}</div>
                              <div className="settings-theme-preview-line is-long" />
                              <div className="settings-theme-preview-line is-short" />
                            </div>
                          </div>

                          <button
                            type="button"
                            className={appearance.theme === option.id ? "settings-theme-action is-active" : "settings-theme-action"}
                            onClick={() => {
                              setTheme(option.id);
                            }}
                          >
                            {appearance.theme === option.id ? "Aktiv" : "Aktivieren"}
                          </button>
                        </article>
                      ))}
                    </div>
                  </SettingsSection>

                  <SettingsSection title="Typografie" description="Schriftstil und Lesefrequenz live anpassen.">
                    <div className="settings-option-grid">
                      {FONT_OPTIONS.map((option) => (
                        <button
                          key={option.id}
                          type="button"
                          className={appearance.font_preset === option.id ? "settings-option-card is-active" : "settings-option-card"}
                          onClick={() => {
                            setFontPreset(option.id);
                          }}
                        >
                          <span className="settings-option-title">{option.label}</span>
                          <span className="settings-option-preview" style={{ fontFamily: option.sample_font }}>
                            Die Geschichte wartet auf deinen nächsten Zug.
                          </span>
                        </button>
                      ))}
                    </div>

                    <div className="settings-option-grid">
                      {SIZE_OPTIONS.map((option) => (
                        <button
                          key={option.id}
                          type="button"
                          className={appearance.font_size === option.id ? "settings-option-card is-active" : "settings-option-card"}
                          onClick={() => {
                            setFontSize(option.id);
                          }}
                        >
                          <span className="settings-option-title">{option.label}</span>
                          <span className="settings-option-preview" style={{ fontSize: `${option.preview_px}px` }}>
                            Vorschau Aelunor Text
                          </span>
                        </button>
                      ))}
                    </div>
                  </SettingsSection>

                  <SettingsSection title="Flächengewichtung">
                    <div className="settings-field-list">
                      <SettingsField label="UI-Dichte" description="Steuert vertikale Kompaktheit und Abstände in der Oberfläche.">
                        <SettingsSegmented<UiDensityId>
                          value={appearance.density}
                          options={[
                            { value: "compact", label: "Kompakt" },
                            { value: "standard", label: "Standard" },
                            { value: "comfortable", label: "Großzügig" },
                          ]}
                          on_change={setDensity}
                        />
                      </SettingsField>
                      <SettingsField label="Storybreite" description="Begrenzt die Lesebreite der Erzähltexte im Play-Bereich.">
                        <SettingsSegmented<StoryWidthId>
                          value={appearance.story_width}
                          options={[
                            { value: "focused", label: "Fokussiert" },
                            { value: "standard", label: "Standard" },
                            { value: "wide", label: "Breit" },
                          ]}
                          on_change={setStoryWidth}
                        />
                      </SettingsField>
                    </div>
                  </SettingsSection>
                </>
              ) : null}

              {activeCategory === "interaction" ? (
                <SettingsSection title="Lesefluss & Bedienung" description="Steuert Timeline-, Composer- und Navigationsverhalten lokal.">
                  <div className="settings-field-list">
                    <SettingsField
                      label="Automatisches Nachziehen in der Timeline"
                      description="Bei neuen Zügen bleibt der aktuelle Storyfokus oben im Blick."
                    >
                      <SettingsToggle checked={interaction.auto_scroll} on_change={setAutoScroll} />
                    </SettingsField>
                    <SettingsField label="Timeline-Details standardmäßig" description="Wie Änderungsblöcke pro Zug initial dargestellt werden.">
                      <SettingsSegmented<TimelineDetailDefault>
                        value={interaction.timeline_detail_default}
                        options={[
                          { value: "collapsed", label: "Eingeklappt" },
                          { value: "expanded", label: "Offen" },
                        ]}
                        on_change={setTimelineDetailDefault}
                      />
                    </SettingsField>
                    <SettingsField label="Composer-Startmodus" description="Welcher Modus beim Öffnen des Play-Screens vorausgewählt ist.">
                      <SettingsSegmented<ComposerModePreference>
                        value={interaction.composer_mode_preference}
                        options={[
                          { value: "do", label: "Tun" },
                          { value: "say", label: "Sagen" },
                          { value: "story", label: "Story" },
                        ]}
                        on_change={setComposerModePreference}
                      />
                    </SettingsField>
                    <SettingsField
                      label="Kritische Aktionen bestätigen"
                      description="Fragt z. B. beim Verlassen der Session noch einmal nach."
                    >
                      <SettingsToggle checked={interaction.confirm_leave} on_change={setConfirmLeave} />
                    </SettingsField>
                    <SettingsField
                      label="Filter und Panelzustände merken"
                      description="Behält lokal zuletzt genutzte Szenenfilter und Rail-Zustände."
                    >
                      <SettingsToggle checked={interaction.remember_filters} on_change={setRememberFilters} />
                    </SettingsField>
                    <SettingsField label="Tastenkürzel aktiv" description="Aktiviert Tastenkürzel in unterstützten Bereichen.">
                      <SettingsToggle checked={interaction.shortcuts_enabled} on_change={setShortcutsEnabled} />
                    </SettingsField>
                    <SettingsField label="Shortcut-Hinweise anzeigen" description="Zeigt verfügbare Kürzel bei passenden Aktionen an.">
                      <SettingsToggle checked={interaction.shortcut_hints} on_change={setShortcutHints} />
                    </SettingsField>
                    <SettingsField label="Tooltip-Intensität" description="Steuert, wie ausführlich kontextuelle Hinweise dargestellt werden.">
                      <SettingsSegmented<TooltipIntensity>
                        value={interaction.tooltip_intensity}
                        options={[
                          { value: "reduced", label: "Reduziert" },
                          { value: "standard", label: "Standard" },
                          { value: "enhanced", label: "Ausführlich" },
                        ]}
                        on_change={setTooltipIntensity}
                      />
                    </SettingsField>
                  </div>
                </SettingsSection>
              ) : null}

              {activeCategory === "accessibility" ? (
                <SettingsSection title="Barrierefreiheit" description="Globale Lesbarkeit und Fokusführung für alle v1-Flächen.">
                  <div className="settings-field-list">
                    <SettingsField label="Bewegung reduzieren" description="Dämpft Übergänge und Mikroanimationen.">
                      <SettingsToggle checked={accessibility.reduced_motion} on_change={setReducedMotion} />
                    </SettingsField>
                    <SettingsField label="Stärkerer Kontrast" description="Erhöht Text-/Flächenkontrast für bessere Erkennbarkeit.">
                      <SettingsToggle checked={accessibility.high_contrast} on_change={setHighContrast} />
                    </SettingsField>
                    <SettingsField label="Sichtbarere Fokusrahmen" description="Verstärkt Fokusindikatoren für Tastaturnavigation.">
                      <SettingsToggle checked={accessibility.strong_focus} on_change={setStrongFocus} />
                    </SettingsField>
                    <SettingsField label="Größere Interaktionsziele" description="Vergrößert Klickflächen bei Buttons und Eingaben.">
                      <SettingsToggle checked={accessibility.larger_targets} on_change={setLargerTargets} />
                    </SettingsField>
                    <SettingsField label="Lesefreundlicher Modus" description="Ruhigere Zeilenführung und entspannter Lesefluss für Storytext.">
                      <SettingsToggle checked={accessibility.reading_friendly_mode} on_change={setReadingFriendlyMode} />
                    </SettingsField>
                  </div>
                </SettingsSection>
              ) : null}

              {activeCategory === "locale" ? (
                <SettingsSection title="Sprache & Region" description="Formatvorgaben für Datum, Zeit und Zahlen (UI bleibt im MVP deutsch).">
                  <div className="settings-field-list">
                    <SettingsField label="UI-Sprache" description="Vorbereitung für spätere Sprachumschaltung, aktuell mit deutschem Standard.">
                      <SettingsSelect<LanguageId>
                        value={locale.language}
                        options={[
                          { value: "de", label: "Deutsch" },
                          { value: "en", label: "Englisch (vorbereitet)" },
                        ]}
                        on_change={setLanguage}
                      />
                    </SettingsField>
                    <SettingsField label="Zeitformat" description="Wie Uhrzeiten dargestellt werden.">
                      <SettingsSegmented<TimeFormatId>
                        value={locale.time_format}
                        options={[
                          { value: "24h", label: "24h" },
                          { value: "12h", label: "12h" },
                        ]}
                        on_change={setTimeFormat}
                      />
                    </SettingsField>
                    <SettingsField label="Datumsformat" description="Steuert die Reihenfolge von Tag/Monat/Jahr.">
                      <SettingsSegmented<DateFormatId>
                        value={locale.date_format}
                        options={[
                          { value: "locale", label: "Lokal" },
                          { value: "dmy", label: "TT.MM.JJJJ" },
                          { value: "mdy", label: "MM/DD/YYYY" },
                          { value: "ymd", label: "YYYY-MM-DD" },
                        ]}
                        on_change={setDateFormat}
                      />
                    </SettingsField>
                    <SettingsField label="Zahlenformat" description="Regelt Trennzeichen und Gruppierung bei numerischen Werten.">
                      <SettingsSegmented<NumberFormatId>
                        value={locale.number_format}
                        options={[
                          { value: "locale", label: "Lokal" },
                          { value: "de", label: "Deutsch" },
                          { value: "en", label: "Englisch" },
                        ]}
                        on_change={setNumberFormat}
                      />
                    </SettingsField>
                  </div>
                </SettingsSection>
              ) : null}

              {activeCategory === "data" ? (
                <SettingsSection title="Daten & Zurücksetzen" description="Verwaltet ausschließlich lokale Browserdaten und Komfortzustände.">
                  <div className="settings-field-list">
                    <SettingsField label="Lokale Einstellungen zurücksetzen" description="Setzt alle Präferenzen auf den Aelunor-Standard zurück.">
                      <button
                        type="button"
                        className="btn ghost settings-danger-action"
                        onClick={() => {
                          if (
                            window.confirm(
                              "Alle lokalen Einstellungen auf Standard zurücksetzen? Kampagnen- und Storydaten bleiben unverändert.",
                            )
                          ) {
                            resetSettings();
                          }
                        }}
                      >
                        Einstellungen zurücksetzen
                      </button>
                    </SettingsField>
                    <SettingsField
                      label="Lokale Komfortdaten löschen"
                      description="Entfernt z. B. lokale Session-Liste, Novelty und UI-Merkzustände. Aktive Session-Credentials bleiben erhalten."
                    >
                      <button
                        type="button"
                        className="btn ghost settings-danger-action"
                        onClick={() => {
                          if (
                            window.confirm(
                              "Lokale Komfortdaten löschen? Aktive Session-Credentials bleiben erhalten.",
                            )
                          ) {
                            clearLocalComfortData();
                          }
                        }}
                      >
                        Komfortdaten löschen
                      </button>
                    </SettingsField>
                    <div className="settings-data-meta status-muted">
                      <p>
                        Zurücksetzbare Buckets:
                        {" "}
                        Namen {localDataMeta.resettable_local_names ? "✓" : "—"},
                        {" "}
                        Entwürfe {localDataMeta.resettable_drafts ? "✓" : "—"},
                        {" "}
                        Filter {localDataMeta.resettable_filters ? "✓" : "—"}
                      </p>
                      <p>
                        Audio/Benachrichtigungen sind technisch vorbereitet und werden in einer späteren Phase als eigene
                        Kategorie freigeschaltet.
                      </p>
                    </div>
                  </div>
                </SettingsSection>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

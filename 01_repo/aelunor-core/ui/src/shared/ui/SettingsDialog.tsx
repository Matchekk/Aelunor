import { useMemo, useRef, useState } from "react";

import { SettingsAppearanceSection, SettingsGameplaySection, SettingsReadingSection } from "./settings/SettingsCoreSections";
import { SettingsDiagnosticsSection, SettingsPrivacySection } from "./settings/SettingsSafetySections";
import { SettingsGmSection } from "./settings/SettingsGmSection";
import { useSurfaceLayer } from "./useSurfaceLayer";

interface SettingsDialogProps {
  open: boolean;
  on_close: () => void;
  return_focus_element?: HTMLElement | null;
}

type SettingsCategory = "gm" | "appearance" | "reading" | "gameplay" | "privacy" | "diagnostics";

const SETTINGS_UI_MEMORY_KEY = "aelunorSettingsUiMemoryV2";

const CATEGORY_ITEMS: Array<{ id: SettingsCategory; label: string; description: string }> = [
  { id: "gm", label: "GM & KI", description: "Provider, Ollama und Modell" },
  { id: "appearance", label: "Darstellung", description: "Theme, Dichte und Bewegung" },
  { id: "reading", label: "Text & Lesbarkeit", description: "Schriften, Größe und Zeilenhöhe" },
  { id: "gameplay", label: "Spielgefühl", description: "Pacing, Zufall und Hinweise" },
  { id: "privacy", label: "Daten & Sicherheit", description: "Lokale Daten und API-Freigaben" },
  { id: "diagnostics", label: "Diagnose", description: "Entwickler- und Statusflächen" },
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

function renderCategory(category: SettingsCategory) {
  switch (category) {
    case "gm":
      return <SettingsGmSection />;
    case "appearance":
      return <SettingsAppearanceSection />;
    case "reading":
      return <SettingsReadingSection />;
    case "gameplay":
      return <SettingsGameplaySection />;
    case "privacy":
      return <SettingsPrivacySection />;
    case "diagnostics":
      return <SettingsDiagnosticsSection />;
  }
}

export function SettingsDialog({ open, on_close, return_focus_element = null }: SettingsDialogProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const [activeCategory, setActiveCategory] = useState<SettingsCategory>(() => readCategoryMemory());

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
            <img className="settings-dialog-logo" src="/v1/brand/aelunor-icon-512x512.png" alt="" aria-hidden="true" />
            <span>Einstellungen</span>
          </h2>
          <button type="button" className="btn ghost" onClick={on_close}>
            Schließen
          </button>
        </header>

        <p className="settings-category-description">
          Globale Präferenzen für GM-Modell, Darstellung, Lesefluss und lokale Sicherheit.
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
              {renderCategory(activeCategory)}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

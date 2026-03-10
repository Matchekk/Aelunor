import { useState, useRef } from "react";

import type { FontPresetId, FontSizeId, ThemeId } from "../types/domain";
import { useThemeStore } from "../../entities/theme/store";
import { useSurfaceLayer } from "./useSurfaceLayer";

interface DisplaySettingsDialogProps {
  open: boolean;
  on_close: () => void;
  return_focus_element?: HTMLElement | null;
}

type SettingsSubpoint = "display" | "session";

const THEME_OPTIONS: Array<{ id: ThemeId; label: string; swatches: [string, string, string] }> = [
  { id: "arcane", label: "Arcane", swatches: ["#0f1520", "#1b2a3d", "#7bcaff"] },
  { id: "tavern", label: "Tavern", swatches: ["#1e1510", "#3b291d", "#d99c48"] },
  { id: "glade", label: "Glade", swatches: ["#0e1c18", "#1b3a31", "#66d49b"] },
  { id: "hybrid", label: "Hybrid", swatches: ["#111923", "#2d2a39", "#86d2cb"] },
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
  { id: "small", label: "Small", preview_px: 14 },
  { id: "medium", label: "Medium", preview_px: 16 },
  { id: "large", label: "Large", preview_px: 18 },
];

export function DisplaySettingsDialog({ open, on_close, return_focus_element = null }: DisplaySettingsDialogProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const [activeSubpoint, setActiveSubpoint] = useState<SettingsSubpoint>("display");
  const theme = useThemeStore((state) => state.theme);
  const fontPreset = useThemeStore((state) => state.font_preset);
  const fontSize = useThemeStore((state) => state.font_size);
  const setTheme = useThemeStore((state) => state.setTheme);
  const setFontPreset = useThemeStore((state) => state.setFontPreset);
  const setFontSize = useThemeStore((state) => state.setFontSize);

  useSurfaceLayer({
    open,
    kind: "modal",
    priority: 42,
    container: dialogRef.current,
    return_focus_element,
    on_close,
  });

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
        aria-label="Display settings"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="v1-panel-head">
          <h2>Einstellungen</h2>
          <button type="button" className="btn ghost" onClick={on_close}>
            Schließen
          </button>
        </header>
        <div className="settings-dialog-layout">
          <nav className="settings-subnav" aria-label="Settings sections">
            <button
              type="button"
              className={activeSubpoint === "display" ? "settings-subnav-item is-active" : "settings-subnav-item"}
              onClick={() => {
                setActiveSubpoint("display");
              }}
            >
              Darstellung
            </button>
            <button
              type="button"
              className={activeSubpoint === "session" ? "settings-subnav-item is-active" : "settings-subnav-item"}
              onClick={() => {
                setActiveSubpoint("session");
              }}
            >
              Session
            </button>
          </nav>

          <div className="settings-dialog-content">
            {activeSubpoint === "display" ? (
              <div className="settings-content-stack">
                <section className="settings-group">
                  <header>
                    <h3>Theme</h3>
                    <p className="status-muted">Farbstil mit Vorschau auswählen.</p>
                  </header>
                  <div className="settings-option-grid">
                    {THEME_OPTIONS.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        className={theme === option.id ? "settings-option-card is-active" : "settings-option-card"}
                        onClick={() => {
                          setTheme(option.id);
                        }}
                      >
                        <span className="settings-option-title">{option.label}</span>
                        <span className="settings-swatch-row" aria-hidden="true">
                          <span style={{ background: option.swatches[0] }} />
                          <span style={{ background: option.swatches[1] }} />
                          <span style={{ background: option.swatches[2] }} />
                        </span>
                        <span className="settings-option-preview">Kampagne fortsetzen</span>
                      </button>
                    ))}
                  </div>
                </section>

                <section className="settings-group">
                  <header>
                    <h3>Schriftstil</h3>
                    <p className="status-muted">Lesestil mit Live-Vorschau.</p>
                  </header>
                  <div className="settings-option-grid">
                    {FONT_OPTIONS.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        className={fontPreset === option.id ? "settings-option-card is-active" : "settings-option-card"}
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
                </section>

                <section className="settings-group">
                  <header>
                    <h3>Schriftgröße</h3>
                    <p className="status-muted">Textgröße für Hub und Play.</p>
                  </header>
                  <div className="settings-option-grid">
                    {SIZE_OPTIONS.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        className={fontSize === option.id ? "settings-option-card is-active" : "settings-option-card"}
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
                </section>
              </div>
            ) : (
              <section className="settings-group">
                <header>
                  <h3>Session</h3>
                  <p className="status-muted">Schnellzugriffe außerhalb der Darstellung.</p>
                </header>
                <div className="settings-session-actions">
                  <a className="btn ghost" href="/">
                    Legacy UI öffnen
                  </a>
                </div>
              </section>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

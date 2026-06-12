import type {
  AppearanceUiDensityId,
  AutoSummaryTurns,
  FixedLocationThemeId,
  GlowIntensityId,
  LocationThemeModeId,
  RandomnessId,
  ReadingTextSizeId,
  StoryLineHeightId,
  ThemeModeId,
  TurnModeId,
} from "../../../entities/settings/types";
import { useUserSettingsStore } from "../../../entities/settings/store";
import type { FontPresetId } from "../../types/domain";
import { SettingsField, SettingsSection, SettingsSegmented, SettingsSelect, SettingsToggle } from "./SettingsFields";

export function SettingsAppearanceSection() {
  const appearance = useUserSettingsStore((state) => state.appearance);
  const patchAppearance = useUserSettingsStore((state) => state.patch_appearance);

  return (
    <SettingsSection title="Darstellung" description="Oberfläche, Ortsstimmung und Bewegung.">
      <div className="settings-field-list">
        <SettingsField label="Theme-Modus">
          <SettingsSegmented<ThemeModeId>
            value={appearance.themeMode}
            options={[
              { value: "aelunor-dark", label: "Aelunor" },
              { value: "high-contrast", label: "Kontrast" },
              { value: "system", label: "System" },
            ]}
            on_change={(themeMode) => patchAppearance({ themeMode })}
          />
        </SettingsField>
        <SettingsField label="Orts-Theme">
          <SettingsSegmented<LocationThemeModeId>
            value={appearance.locationThemeMode}
            options={[
              { value: "automatic", label: "Automatisch" },
              { value: "fixed", label: "Fest" },
            ]}
            on_change={(locationThemeMode) => patchAppearance({ locationThemeMode })}
          />
        </SettingsField>
        {appearance.locationThemeMode === "fixed" ? (
          <SettingsField label="Fester Ort">
            <SettingsSelect<FixedLocationThemeId>
              value={appearance.fixedLocationTheme}
              options={[
                { value: "default", label: "Standard" },
                { value: "tavern", label: "Taverne" },
                { value: "forest", label: "Wald" },
                { value: "frostlands", label: "Frostlande" },
                { value: "dungeon", label: "Dungeon" },
                { value: "city", label: "Stadt" },
                { value: "temple", label: "Tempel" },
              ]}
              on_change={(fixedLocationTheme) => patchAppearance({ fixedLocationTheme })}
            />
          </SettingsField>
        ) : null}
        <SettingsField label="UI-Dichte">
          <SettingsSegmented<AppearanceUiDensityId>
            value={appearance.uiDensity}
            options={[
              { value: "compact", label: "Kompakt" },
              { value: "comfortable", label: "Komfort" },
              { value: "cinematic", label: "Kino" },
            ]}
            on_change={(uiDensity) => patchAppearance({ uiDensity })}
          />
        </SettingsField>
        <SettingsField label="Glow">
          <SettingsSegmented<GlowIntensityId>
            value={appearance.glowIntensity}
            options={[
              { value: "normal", label: "Normal" },
              { value: "low", label: "Niedrig" },
              { value: "off", label: "Aus" },
            ]}
            on_change={(glowIntensity) => patchAppearance({ glowIntensity })}
          />
        </SettingsField>
        <SettingsField label="Bewegung reduzieren">
          <SettingsToggle checked={appearance.reducedMotion} on_change={(reducedMotion) => patchAppearance({ reducedMotion })} />
        </SettingsField>
      </div>
    </SettingsSection>
  );
}

export function SettingsReadingSection() {
  const reading = useUserSettingsStore((state) => state.reading);
  const patchReading = useUserSettingsStore((state) => state.patch_reading);

  return (
    <SettingsSection title="Text & Lesbarkeit" description="Storytext bleibt lesbar, Fantasy bleibt in Akzenten.">
      <div className="settings-field-list">
        <SettingsField label="Font-Preset">
          <SettingsSelect<FontPresetId>
            value={reading.fontPreset}
            options={[
              { value: "aelunor-classic", label: "Aelunor Classic" },
              { value: "book-mode", label: "Book Mode" },
              { value: "readable", label: "Readable Mode" },
              { value: "literary-fantasy", label: "Literary Fantasy" },
              { value: "international", label: "International Fallback" },
            ]}
            on_change={(fontPreset) => patchReading({ fontPreset })}
          />
        </SettingsField>
        <SettingsField label="Textgröße">
          <SettingsSegmented<ReadingTextSizeId>
            value={reading.textSize}
            options={[
              { value: "small", label: "Klein" },
              { value: "medium", label: "Mittel" },
              { value: "large", label: "Groß" },
              { value: "extra-large", label: "XL" },
            ]}
            on_change={(textSize) => patchReading({ textSize })}
          />
        </SettingsField>
        <SettingsField label="Story-Zeilenhöhe">
          <SettingsSegmented<StoryLineHeightId>
            value={reading.storyLineHeight}
            options={[
              { value: "normal", label: "Normal" },
              { value: "comfortable", label: "Komfort" },
              { value: "spacious", label: "Weit" },
            ]}
            on_change={(storyLineHeight) => patchReading({ storyLineHeight })}
          />
        </SettingsField>
      </div>
    </SettingsSection>
  );
}

export function SettingsGameplaySection() {
  const gameplay = useUserSettingsStore((state) => state.gameplay);
  const patchGameplay = useUserSettingsStore((state) => state.patch_gameplay);

  return (
    <SettingsSection title="Spielgefühl" description="Pacing und Hilfen für den Spieltisch.">
      <div className="settings-field-list">
        <SettingsField label="Turn-Modus">
          <SettingsSegmented<TurnModeId>
            value={gameplay.turnMode}
            options={[
              { value: "story-first", label: "Story" },
              { value: "balanced", label: "Balance" },
              { value: "rules-aware", label: "Regeln" },
            ]}
            on_change={(turnMode) => patchGameplay({ turnMode })}
          />
        </SettingsField>
        <SettingsField label="Zufall">
          <SettingsSegmented<RandomnessId>
            value={gameplay.randomness}
            options={[
              { value: "low", label: "Niedrig" },
              { value: "normal", label: "Normal" },
              { value: "high", label: "Hoch" },
            ]}
            on_change={(randomness) => patchGameplay({ randomness })}
          />
        </SettingsField>
        <SettingsField label="Hinweise anzeigen">
          <SettingsToggle checked={gameplay.showHints} on_change={(showHints) => patchGameplay({ showHints })} />
        </SettingsField>
        <SettingsField label="Auto-Zusammenfassung">
          <SettingsSelect<`${AutoSummaryTurns}`>
            value={`${gameplay.autoSummaryTurns}` as `${AutoSummaryTurns}`}
            options={[
              { value: "0", label: "Aus" },
              { value: "10", label: "Alle 10 Turns" },
              { value: "20", label: "Alle 20 Turns" },
              { value: "30", label: "Alle 30 Turns" },
            ]}
            on_change={(autoSummaryTurns) => patchGameplay({ autoSummaryTurns: Number(autoSummaryTurns) as AutoSummaryTurns })}
          />
        </SettingsField>
      </div>
    </SettingsSection>
  );
}

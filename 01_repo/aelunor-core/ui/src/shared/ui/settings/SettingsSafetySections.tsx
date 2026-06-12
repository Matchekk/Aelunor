import { useUserSettingsStore } from "../../../entities/settings/store";
import { SettingsField, SettingsSection, SettingsToggle } from "./SettingsFields";

export function SettingsPrivacySection() {
  const privacy = useUserSettingsStore((state) => state.privacy);
  const localDataMeta = useUserSettingsStore((state) => state.local_data_meta);
  const patchPrivacy = useUserSettingsStore((state) => state.patch_privacy);
  const resetSettings = useUserSettingsStore((state) => state.reset_settings);
  const clearLocalComfortData = useUserSettingsStore((state) => state.clear_local_comfort_data);

  return (
    <SettingsSection title="Daten & Sicherheit" description="Lokale Modelle und lokale Browserdaten.">
      <div className="settings-field-list">
        <SettingsField label="Lokale Modelle bevorzugen">
          <SettingsToggle checked={privacy.preferLocalModels} on_change={(preferLocalModels) => patchPrivacy({ preferLocalModels })} />
        </SettingsField>
        <SettingsField label="Externe API-Aufrufe erlauben">
          <SettingsToggle checked={privacy.allowExternalApiCalls} on_change={(allowExternalApiCalls) => patchPrivacy({ allowExternalApiCalls })} />
        </SettingsField>
        <SettingsField label="Diagnosedaten anonymisieren">
          <SettingsToggle checked={privacy.anonymizeDiagnostics} on_change={(anonymizeDiagnostics) => patchPrivacy({ anonymizeDiagnostics })} />
        </SettingsField>
        <SettingsField label="Lokale Einstellungen zurücksetzen">
          <button
            type="button"
            className="btn ghost settings-danger-action"
            onClick={() => {
              if (window.confirm("Alle lokalen Einstellungen auf Standard zurücksetzen? Kampagnen- und Storydaten bleiben unverändert.")) {
                resetSettings();
              }
            }}
          >
            Einstellungen zurücksetzen
          </button>
        </SettingsField>
        <SettingsField label="Lokale Komfortdaten löschen">
          <button
            type="button"
            className="btn ghost settings-danger-action"
            onClick={() => {
              if (window.confirm("Lokale Komfortdaten löschen? Aktive Session-Credentials bleiben erhalten.")) {
                clearLocalComfortData();
              }
            }}
          >
            Komfortdaten löschen
          </button>
        </SettingsField>
        <div className="settings-data-meta status-muted">
          <p>
            Zurücksetzbar: Namen {localDataMeta.resettable_local_names ? "ja" : "nein"}, Entwürfe{" "}
            {localDataMeta.resettable_drafts ? "ja" : "nein"}, Filter {localDataMeta.resettable_filters ? "ja" : "nein"}.
          </p>
        </div>
      </div>
    </SettingsSection>
  );
}

export function SettingsDiagnosticsSection() {
  const diagnostics = useUserSettingsStore((state) => state.diagnostics);
  const patchDiagnostics = useUserSettingsStore((state) => state.patch_diagnostics);
  const meta = useUserSettingsStore((state) => state.meta);
  const gm = useUserSettingsStore((state) => state.gm);

  return (
    <SettingsSection title="Diagnose" description="Entwicklerflächen bleiben standardmäßig verborgen.">
      <div className="settings-field-list">
        <SettingsField label="Developer Panel anzeigen">
          <SettingsToggle
            checked={diagnostics.showDeveloperPanel}
            on_change={(showDeveloperPanel) => patchDiagnostics({ showDeveloperPanel })}
          />
        </SettingsField>
        {diagnostics.showDeveloperPanel ? (
          <div className="settings-data-meta status-muted">
            <p>Settings Schema v{meta.schema_version}</p>
            <p>GM Provider: {gm.provider}</p>
            <p>GM Modell: {gm.model ?? "nicht gewählt"}</p>
          </div>
        ) : null}
      </div>
    </SettingsSection>
  );
}

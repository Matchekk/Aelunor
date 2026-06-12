import { useState } from "react";

import { fetchLlmModels, testGmModel } from "../../../entities/settings/gmApi";
import type { GmProviderId } from "../../../entities/settings/types";
import { useUserSettingsStore } from "../../../entities/settings/store";
import type { LlmModelInfo } from "../../api/contracts";
import { SettingsField, SettingsSection, SettingsSelect } from "./SettingsFields";

type GmConnectionState = "idle" | "loading" | "connected" | "offline" | "error";

export function SettingsGmSection() {
  const gm = useUserSettingsStore((state) => state.gm);
  const patchGm = useUserSettingsStore((state) => state.patch_gm);
  const [models, setModels] = useState<LlmModelInfo[]>([]);
  const [status, setStatus] = useState<GmConnectionState>("idle");
  const [message, setMessage] = useState("Noch nicht gescannt.");
  const [testing, setTesting] = useState(false);

  const modelOptions = models.some((model) => model.name === gm.model)
    ? models
    : gm.model
      ? [{ name: gm.model }, ...models]
      : models;

  async function scanModels() {
    setStatus("loading");
    setMessage("Suche lokale Ollama-Modelle ...");
    try {
      const result = await fetchLlmModels(gm.ollamaBaseUrl);
      setModels(result.models);
      setStatus(result.status);
      setMessage(result.message);
      if (!gm.model && result.models[0]?.name) {
        patchGm({ model: result.models[0].name });
      }
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Modellscan fehlgeschlagen.");
    }
  }

  async function testModel() {
    setTesting(true);
    setMessage("Teste GM-Modell ...");
    try {
      const result = await testGmModel({ ollamaBaseUrl: gm.ollamaBaseUrl, model: gm.model });
      setStatus(result.ok ? "connected" : "error");
      setMessage(result.latencyMs ? `${result.message} (${result.latencyMs} ms)` : result.message);
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "GM-Test fehlgeschlagen.");
    } finally {
      setTesting(false);
    }
  }

  return (
    <SettingsSection title="GM & KI" description="Lokales GM-Modell auswählen und kurz prüfen.">
      <div className="settings-field-list">
        <SettingsField label="Provider" description="In Phase 1 ist nur Ollama aktiv verdrahtet.">
          <SettingsSelect<GmProviderId>
            value={gm.provider}
            options={[
              { value: "ollama", label: "Ollama lokal" },
              { value: "custom-openai-compatible", label: "OpenAI-kompatibel (vorbereitet)" },
              { value: "mock", label: "Mock" },
            ]}
            on_change={(provider) => patchGm({ provider })}
          />
        </SettingsField>

        <SettingsField label="Ollama Base URL">
          <input
            type="url"
            value={gm.ollamaBaseUrl}
            spellCheck={false}
            onChange={(event) => patchGm({ ollamaBaseUrl: event.target.value })}
          />
        </SettingsField>

        <SettingsField label="GM Model" description="Modelle werden über die lokale Ollama API gelesen.">
          <div className="settings-inline-actions">
            <select
              className="settings-select"
              value={gm.model ?? ""}
              onChange={(event) => patchGm({ model: event.target.value || null })}
            >
              <option value="">Kein Modell gewählt</option>
              {modelOptions.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.name}
                </option>
              ))}
            </select>
            <button type="button" className="btn ghost" onClick={scanModels} disabled={status === "loading"}>
              Modelle neu scannen
            </button>
            <button type="button" className="btn ghost" onClick={testModel} disabled={testing || !gm.model}>
              GM testen
            </button>
          </div>
          <p className={`settings-status-line is-${status}`}>{message}</p>
        </SettingsField>
      </div>
    </SettingsSection>
  );
}

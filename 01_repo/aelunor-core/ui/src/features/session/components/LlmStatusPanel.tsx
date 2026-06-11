import { useQuery } from "@tanstack/react-query";

import type { LlmStatusResponse } from "../../../shared/api/contracts";
import { endpoints } from "../../../shared/api/endpoints";
import { getJson } from "../../../shared/api/httpClient";
import { normalizeLlmStatusResponse } from "../llmStatusModel";

const LLM_STATUS_TIMEOUT_MS = 3_000;

async function fetchLlmStatus(): Promise<LlmStatusResponse> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), LLM_STATUS_TIMEOUT_MS);

  try {
    return await getJson<LlmStatusResponse>(endpoints.system.llm_status(), {
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("LLM-Status antwortet nicht rechtzeitig.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function LlmStatusPanel() {
  const statusQuery = useQuery({
    queryKey: ["llm", "status"],
    queryFn: fetchLlmStatus,
    retry: 0,
    staleTime: 30_000,
  });

  if (statusQuery.isPending) {
    return (
      <section className="v1-panel llm-status-panel">
        <div className="v1-panel-head">
          <h2>LLM-Status</h2>
        </div>
        <p className="status-muted">Status wird geladen...</p>
      </section>
    );
  }

  if (statusQuery.isError || !statusQuery.data) {
    return (
      <section className="v1-panel llm-status-panel">
        <div className="v1-panel-head">
          <h2>LLM-Status</h2>
        </div>
        <p className="status-muted">Status nicht verfügbar. Der Session-Hub bleibt ohne diese Statusabfrage nutzbar.</p>
      </section>
    );
  }

  const view = normalizeLlmStatusResponse(statusQuery.data);

  return (
    <section className="v1-panel llm-status-panel">
      <div className="v1-panel-head">
        <h2>LLM-Status</h2>
      </div>
      <dl className="meta-list">
        <div>
          <dt>Anbieter</dt>
          <dd>{view.provider_label}</dd>
        </div>
        <div>
          <dt>Ollama erreichbar</dt>
          <dd>{view.ollama_ok ? "Ja" : "Nein"}</dd>
        </div>
        <div>
          <dt>Konfiguriertes Modell</dt>
          <dd>{view.configured_model}</dd>
        </div>
        <div>
          <dt>Modell verfügbar</dt>
          <dd>{view.configured_model_available ? "Ja" : "Nein"}</dd>
        </div>
        <div>
          <dt>Gefundene Modelle</dt>
          <dd>{view.available_models_count}</dd>
        </div>
        <div>
          <dt>Timeout</dt>
          <dd>{view.request_timeout_sec}</dd>
        </div>
        {view.fallback_note ? (
          <div>
            <dt>Fallback</dt>
            <dd>{view.fallback_note}</dd>
          </div>
        ) : null}
      </dl>
      {view.error ? <p className="status-muted">Fehler: {view.error}</p> : null}
    </section>
  );
}

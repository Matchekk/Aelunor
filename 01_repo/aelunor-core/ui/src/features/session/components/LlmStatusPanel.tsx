import { useQuery } from "@tanstack/react-query";

import type { LlmStatusResponse } from "../../../shared/api/contracts";
import { endpoints } from "../../../shared/api/endpoints";
import { getJson } from "../../../shared/api/httpClient";

async function fetchLlmStatus(): Promise<LlmStatusResponse> {
  return getJson<LlmStatusResponse>(endpoints.system.llm_status());
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

interface LlmStatusView {
  ollama_ok: boolean;
  configured_model: string;
  configured_model_available: boolean;
  available_models_count: number;
  request_timeout_sec: string;
  error: string;
}

// The status endpoint changed from a flat payload to {provider, primary: {...}, fallback: {...}};
// read both shapes defensively so the hub never crashes on a contract drift.
function deriveLlmStatusView(payload: unknown): LlmStatusView {
  const raw = readRecord(payload);
  const primary = "primary" in raw ? readRecord(raw.primary) : raw;
  const timeout = primary.request_timeout_sec;
  return {
    ollama_ok: primary.ollama_ok === true,
    configured_model: typeof primary.configured_model === "string" && primary.configured_model ? primary.configured_model : "unbekannt",
    configured_model_available: primary.configured_model_available === true,
    available_models_count: Array.isArray(primary.available_models) ? primary.available_models.length : 0,
    request_timeout_sec: typeof timeout === "number" && Number.isFinite(timeout) ? String(timeout) : "—",
    error: typeof primary.error === "string" ? primary.error : "",
  };
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
          <h2>LLM Status</h2>
        </div>
        <p className="status-muted">Loading...</p>
      </section>
    );
  }

  if (statusQuery.isError || !statusQuery.data) {
    return (
      <section className="v1-panel llm-status-panel">
        <div className="v1-panel-head">
          <h2>LLM Status</h2>
        </div>
        <p className="status-muted">Status unavailable. Session Hub remains fully usable without this endpoint.</p>
      </section>
    );
  }

  const view = deriveLlmStatusView(statusQuery.data);

  return (
    <section className="v1-panel llm-status-panel">
      <div className="v1-panel-head">
        <h2>LLM Status</h2>
      </div>
      <dl className="meta-list">
        <div>
          <dt>ollama_ok</dt>
          <dd>{view.ollama_ok ? "true" : "false"}</dd>
        </div>
        <div>
          <dt>configured_model</dt>
          <dd>{view.configured_model}</dd>
        </div>
        <div>
          <dt>configured_model_available</dt>
          <dd>{view.configured_model_available ? "true" : "false"}</dd>
        </div>
        <div>
          <dt>available_models</dt>
          <dd>{view.available_models_count}</dd>
        </div>
        <div>
          <dt>request_timeout_sec</dt>
          <dd>{view.request_timeout_sec}</dd>
        </div>
      </dl>
      {view.error ? <p className="status-muted">error: {view.error}</p> : null}
    </section>
  );
}

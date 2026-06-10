import { useQuery } from "@tanstack/react-query";

import type { LlmStatusResponse } from "../../../shared/api/contracts";
import { endpoints } from "../../../shared/api/endpoints";
import { getJson } from "../../../shared/api/httpClient";
import { normalizeLlmStatusResponse } from "../llmStatusModel";

async function fetchLlmStatus(): Promise<LlmStatusResponse> {
  return getJson<LlmStatusResponse>(endpoints.system.llm_status());
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

  const view = normalizeLlmStatusResponse(statusQuery.data);

  return (
    <section className="v1-panel llm-status-panel">
      <div className="v1-panel-head">
        <h2>LLM Status</h2>
      </div>
      <dl className="meta-list">
        <div>
          <dt>provider</dt>
          <dd>{view.provider_label}</dd>
        </div>
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
        {view.fallback_note ? (
          <div>
            <dt>fallback</dt>
            <dd>{view.fallback_note}</dd>
          </div>
        ) : null}
      </dl>
      {view.error ? <p className="status-muted">error: {view.error}</p> : null}
    </section>
  );
}

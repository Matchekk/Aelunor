import { useQuery } from "@tanstack/react-query";

import type { LlmStatusResponse } from "../../../shared/api/contracts";
import { endpoints } from "../../../shared/api/endpoints";
import { getJson } from "../../../shared/api/httpClient";

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

  const data = statusQuery.data;

  return (
    <section className="v1-panel llm-status-panel">
      <div className="v1-panel-head">
        <h2>LLM Status</h2>
      </div>
      <dl className="meta-list">
        <div>
          <dt>ollama_ok</dt>
          <dd>{data.ollama_ok ? "true" : "false"}</dd>
        </div>
        <div>
          <dt>configured_model</dt>
          <dd>{data.configured_model}</dd>
        </div>
        <div>
          <dt>configured_model_available</dt>
          <dd>{data.configured_model_available ? "true" : "false"}</dd>
        </div>
        <div>
          <dt>available_models</dt>
          <dd>{data.available_models.length}</dd>
        </div>
        <div>
          <dt>request_timeout_sec</dt>
          <dd>{data.request_timeout_sec}</dd>
        </div>
      </dl>
      {data.error ? <p className="status-muted">error: {data.error}</p> : null}
    </section>
  );
}

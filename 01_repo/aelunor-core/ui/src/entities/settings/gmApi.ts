import { endpoints } from "../../shared/api/endpoints";
import type { LlmModelsResponse, LlmTestResponse } from "../../shared/api/contracts";

interface GmRequestOptions {
  ollamaBaseUrl: string;
  model: string | null;
}

export async function fetchLlmModels(ollamaBaseUrl: string): Promise<LlmModelsResponse> {
  const params = new URLSearchParams({ ollamaBaseUrl });
  const response = await fetch(`${endpoints.system.llm_models()}?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Model scan failed (${response.status})`);
  }
  return (await response.json()) as LlmModelsResponse;
}

export async function testGmModel(options: GmRequestOptions): Promise<LlmTestResponse> {
  const response = await fetch(endpoints.system.llm_test(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ollamaBaseUrl: options.ollamaBaseUrl,
      model: options.model,
    }),
  });
  if (!response.ok) {
    throw new Error(`GM test failed (${response.status})`);
  }
  return (await response.json()) as LlmTestResponse;
}

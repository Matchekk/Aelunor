import type { LlmStatusResponse } from "../../shared/api/contracts";

export interface LlmStatusView {
  provider_label: string;
  ollama_ok: boolean;
  configured_model: string;
  configured_model_available: boolean;
  available_models_count: number;
  request_timeout_sec: string;
  fallback_note: string;
  error: string;
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

// /api/llm/status has three shapes (flat ollama, flat anthropic, nested auto);
// the payload is also accepted as unknown so a future contract drift degrades
// to fallbacks instead of crashing the hub.
export function normalizeLlmStatusResponse(payload: LlmStatusResponse | unknown): LlmStatusView {
  const raw = readRecord(payload);
  const primary = "primary" in raw ? readRecord(raw.primary) : raw;
  const fallback = readRecord(raw.fallback);
  const timeout = primary.request_timeout_sec;
  const fallbackName = readString(fallback.name) || readString(fallback.provider);
  return {
    provider_label: readString(raw.llm_provider) || readString(raw.provider) || readString(primary.name) || "unbekannt",
    ollama_ok: primary.ollama_ok === true,
    configured_model: readString(primary.configured_model) || "unbekannt",
    configured_model_available: primary.configured_model_available === true,
    available_models_count: Array.isArray(primary.available_models) ? primary.available_models.length : 0,
    request_timeout_sec: typeof timeout === "number" && Number.isFinite(timeout) ? String(timeout) : "—",
    fallback_note: fallbackName ? `${fallbackName} (${fallback.anthropic_ok === true ? "bereit" : "nicht bereit"})` : "",
    error: readString(primary.error),
  };
}

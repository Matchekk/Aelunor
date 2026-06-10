import { describe, expect, it } from "vitest";

import type { LlmStatusResponse } from "../../shared/api/contracts";
import { normalizeLlmStatusResponse } from "./llmStatusModel";

function collectStrings(value: unknown, out: string[] = []): string[] {
  if (typeof value === "string") {
    out.push(value);
  } else if (value && typeof value === "object") {
    Object.values(value).forEach((entry) => collectStrings(entry, out));
  }
  return out;
}

describe("normalizeLlmStatusResponse", () => {
  it("normalizes the nested auto shape with primary and fallback", () => {
    const payload: LlmStatusResponse = {
      provider: "auto",
      llm_provider: "auto",
      primary: {
        name: "ollama",
        ollama_url: "http://127.0.0.1:11434",
        configured_model: "llama3.2:3b",
        request_timeout_sec: 240,
        ollama_ok: false,
        configured_model_available: false,
        available_models: [],
        error: "connect timeout",
      },
      fallback: {
        name: "anthropic",
        provider: "anthropic",
        configured_model: "claude-opus-4-8",
        anthropic_ok: true,
      },
    };

    expect(normalizeLlmStatusResponse(payload)).toMatchObject({
      provider_label: "auto",
      ollama_ok: false,
      configured_model: "llama3.2:3b",
      configured_model_available: false,
      available_models_count: 0,
      request_timeout_sec: "240",
      fallback_note: "anthropic (bereit)",
      error: "connect timeout",
    });
  });

  it("normalizes the flat legacy ollama shape", () => {
    const payload: LlmStatusResponse = {
      ollama_url: "http://127.0.0.1:11434",
      configured_model: "llama3.2:3b",
      request_timeout_sec: 120,
      ollama_ok: true,
      configured_model_available: true,
      available_models: [
        { name: "llama3.2:3b", size: 1, parameter_size: "3B", family: "llama" },
        { name: "qwen2.5", size: 2, parameter_size: "7B", family: "qwen" },
      ],
      error: "",
      llm_provider: "ollama",
    };

    const view = normalizeLlmStatusResponse(payload);
    expect(view.provider_label).toBe("ollama");
    expect(view.ollama_ok).toBe(true);
    expect(view.available_models_count).toBe(2);
    expect(view.fallback_note).toBe("");
  });

  it("handles a missing or empty available_models list", () => {
    expect(normalizeLlmStatusResponse({ provider: "auto", primary: { name: "ollama" } }).available_models_count).toBe(0);
    expect(normalizeLlmStatusResponse({ configured_model: "x", available_models: [] }).available_models_count).toBe(0);
  });

  it("marks an unready fallback and tolerates a missing fallback", () => {
    const unready = normalizeLlmStatusResponse({
      provider: "auto",
      primary: { name: "ollama" },
      fallback: { name: "anthropic", anthropic_ok: false },
    });
    expect(unready.fallback_note).toBe("anthropic (nicht bereit)");

    const none = normalizeLlmStatusResponse({ provider: "auto", primary: { name: "ollama" } });
    expect(none.fallback_note).toBe("");
  });

  it("does not crash on minimal or broken payloads", () => {
    for (const payload of [null, undefined, {}, [], "kaputt", { primary: "not-an-object" }, { available_models: "nope" }]) {
      const view = normalizeLlmStatusResponse(payload);
      expect(view.configured_model).toBe("unbekannt");
      expect(view.available_models_count).toBe(0);
      expect(view.request_timeout_sec).toBe("—");
    }
  });

  it("never produces undefined or [object Object] text", () => {
    const payloads: unknown[] = [
      null,
      {},
      { provider: "auto", primary: { configured_model: { nested: true }, error: 42 }, fallback: { name: { x: 1 } } },
    ];
    for (const payload of payloads) {
      for (const text of collectStrings(normalizeLlmStatusResponse(payload))) {
        expect(text).not.toContain("undefined");
        expect(text).not.toContain("[object Object]");
      }
    }
  });
});

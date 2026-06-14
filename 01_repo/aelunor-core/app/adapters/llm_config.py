"""LLM provider selection.

Chooses which LLM backend the app talks to. The local Ollama backend is the
default and preferred GM runtime. Cloud providers are only used when selected
explicitly.

Select the provider with the ``LLM_PROVIDER`` environment variable:

- ``ollama`` (default): local only.
- ``auto``: local only. Kept as a compatibility alias for older configs.
- ``anthropic``: cloud only (Claude).

The Anthropic key is read from the machine environment by the SDK
(``ANTHROPIC_API_KEY`` / ``ANTHROPIC_AUTH_TOKEN``) — never hardcoded. The model
is configurable via ``ANTHROPIC_MODEL`` (default ``claude-opus-4-8``).
"""
import os

from app.adapters.anthropic_adapter import (
    AnthropicAdapter,
    AnthropicSettings,
)
from app.adapters.llama_cpp_adapter import LlamaCppOpenAIAdapter, LlamaCppSettings
from app.adapters.ollama_config import (
    OLLAMA_ADAPTER,
    OLLAMA_NUM_CTX,
    OLLAMA_SEED,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT_SEC,
)

# Provider-Wahl: AELUNOR_LLM_PROVIDER hat Vorrang (vom Loop-Auftrag gefordert),
# sonst LLM_PROVIDER. Default = ollama.
LLM_PROVIDER = (
    os.getenv("AELUNOR_LLM_PROVIDER", "").strip().lower()
    or (os.getenv("LLM_PROVIDER", "ollama") or "ollama").strip().lower()
)

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8").strip()
ANTHROPIC_MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "8192"))
ANTHROPIC_TIMEOUT_SEC = int(os.getenv("ANTHROPIC_TIMEOUT_SEC", "240"))

ANTHROPIC_ADAPTER = AnthropicAdapter(
    AnthropicSettings(
        model=ANTHROPIC_MODEL,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        timeout_sec=ANTHROPIC_TIMEOUT_SEC,
    )
)


# Experimenteller, OpenAI-kompatibler llama.cpp-Provider (Default bleibt Ollama).
LLAMA_CPP_BASE_URL = os.getenv("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8088/v1").rstrip("/")
LLAMA_CPP_MODEL = os.getenv("LLAMA_CPP_MODEL", "gemma-3n-e4b").strip()
LLAMA_CPP_MAX_TOKENS = int(os.getenv("LLAMA_CPP_MAX_TOKENS", "6144"))
# Anti-Repetition-Sampler: llama.cpp default = 1.0 (KEINE Strafe) -> gemma-3n
# laeuft auf Retry-/Repair-Calls in Wiederholungs-Runaways und sprengt das
# Token-Budget (finish_reason=length) -> ungueltiges JSON. Wir spiegeln Ollamas
# Werte, damit der llama.cpp-Provider dieselbe Retry-Stabilitaet bekommt.
from app.adapters.ollama_config import OLLAMA_REPEAT_LAST_N, OLLAMA_REPEAT_PENALTY

LLAMA_CPP_REPEAT_PENALTY = float(os.getenv("LLAMA_CPP_REPEAT_PENALTY", str(OLLAMA_REPEAT_PENALTY)))
LLAMA_CPP_REPEAT_LAST_N = int(os.getenv("LLAMA_CPP_REPEAT_LAST_N", str(OLLAMA_REPEAT_LAST_N)))

LLAMA_CPP_ADAPTER = LlamaCppOpenAIAdapter(
    LlamaCppSettings(
        base_url=LLAMA_CPP_BASE_URL,
        model=LLAMA_CPP_MODEL,
        timeout_sec=OLLAMA_TIMEOUT_SEC,
        temperature=OLLAMA_TEMPERATURE,
        num_ctx=OLLAMA_NUM_CTX,
        max_tokens=LLAMA_CPP_MAX_TOKENS,
        seed=OLLAMA_SEED,
        repeat_penalty=LLAMA_CPP_REPEAT_PENALTY,
        repeat_last_n=LLAMA_CPP_REPEAT_LAST_N,
    )
)


def select_llm_adapter(provider: str):
    """Resolve the active adapter for the requested provider string."""
    if provider == "anthropic":
        return ANTHROPIC_ADAPTER
    if provider in ("llama_cpp_openai", "llama_cpp", "llamacpp"):
        return LLAMA_CPP_ADAPTER
    return OLLAMA_ADAPTER


LLM_ADAPTER = select_llm_adapter(LLM_PROVIDER)

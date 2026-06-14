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
from typing import Mapping, Optional

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

# Provider-Wahl: AELUNOR_LLM_PROVIDER hat Vorrang, sonst LLM_PROVIDER.
# Default = llama_cpp_openai (Produktentscheidung nach PR #59: llama.cpp ist der
# schnelle Standard-Runtime). Ollama ist Legacy/Fallback und muss explizit
# gewaehlt werden (AELUNOR_LLM_PROVIDER=ollama oder LLM_PROVIDER=ollama).
DEFAULT_LLM_PROVIDER = "llama_cpp_openai"


def resolve_provider(env: Optional[Mapping[str, str]] = None) -> str:
    """Resolve the active provider string from the environment.

    Precedence: ``AELUNOR_LLM_PROVIDER`` > ``LLM_PROVIDER`` > default
    (``llama_cpp_openai``). Ollama is never the default — it must be set
    explicitly.
    """
    env = os.environ if env is None else env
    explicit = (env.get("AELUNOR_LLM_PROVIDER", "") or "").strip().lower()
    if explicit:
        return explicit
    return (env.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER) or DEFAULT_LLM_PROVIDER).strip().lower()


LLM_PROVIDER = resolve_provider()

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
    """Resolve the active adapter for the requested provider string.

    Default runtime is llama.cpp; Ollama is legacy/fallback and must be selected
    explicitly (``ollama``). ``auto`` maps to llama.cpp (the recommended local
    default) — kept as a compatibility alias. ``anthropic`` is cloud and never a
    default. Unknown providers raise instead of silently falling back to Ollama,
    so a typo can never quietly make Aelunor slow.
    """
    if provider == "anthropic":
        return ANTHROPIC_ADAPTER
    if provider in ("llama_cpp_openai", "llama_cpp", "llamacpp", "auto"):
        return LLAMA_CPP_ADAPTER
    if provider == "ollama":
        return OLLAMA_ADAPTER
    raise ValueError(
        f"Unknown LLM provider {provider!r}. Valid values: "
        "'llama_cpp_openai' (default), 'ollama' (legacy/fallback), 'anthropic', 'auto'. "
        "Set AELUNOR_LLM_PROVIDER or LLM_PROVIDER."
    )


LLM_ADAPTER = select_llm_adapter(LLM_PROVIDER)

"""LLM provider selection.

Chooses which LLM backend the app talks to. The local Ollama backend stays the
primary / future focus; the Anthropic Claude API is an optional cloud fallback
for machines without a local model.

Select the provider with the ``LLM_PROVIDER`` environment variable:

- ``auto`` (default): use local Ollama, and automatically fall back to Claude
  when Ollama is unreachable — but only if an Anthropic key is present in the
  environment. With no key it behaves exactly like ``ollama``.
- ``ollama``: local only.
- ``anthropic``: cloud only (Claude).

The Anthropic key is read from the machine environment by the SDK
(``ANTHROPIC_API_KEY`` / ``ANTHROPIC_AUTH_TOKEN``) — never hardcoded. The model
is configurable via ``ANTHROPIC_MODEL`` (default ``claude-opus-4-8``).
"""
import os

from app.adapters.anthropic_adapter import (
    AnthropicAdapter,
    AnthropicSettings,
    FallbackLLMAdapter,
    anthropic_key_present,
)
from app.adapters.ollama_config import OLLAMA_ADAPTER

LLM_PROVIDER = (os.getenv("LLM_PROVIDER", "auto") or "auto").strip().lower()

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


def select_llm_adapter(provider: str):
    """Resolve the active adapter for the requested provider string."""
    if provider == "anthropic":
        return ANTHROPIC_ADAPTER
    if provider == "ollama":
        return OLLAMA_ADAPTER
    # auto: local-first, fall back to Claude only when a key is configured.
    if anthropic_key_present():
        return FallbackLLMAdapter(OLLAMA_ADAPTER, ANTHROPIC_ADAPTER)
    return OLLAMA_ADAPTER


LLM_ADAPTER = select_llm_adapter(LLM_PROVIDER)

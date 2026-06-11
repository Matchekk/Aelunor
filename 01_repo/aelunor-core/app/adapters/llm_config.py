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
from app.adapters.ollama_config import OLLAMA_ADAPTER

LLM_PROVIDER = (os.getenv("LLM_PROVIDER", "ollama") or "ollama").strip().lower()

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
    return OLLAMA_ADAPTER


LLM_ADAPTER = select_llm_adapter(LLM_PROVIDER)

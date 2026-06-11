"""Compatibility import path for LLM provider selection."""

from app.adapters.llm_config import (
    ANTHROPIC_ADAPTER,
    ANTHROPIC_MAX_TOKENS,
    ANTHROPIC_MODEL,
    ANTHROPIC_TIMEOUT_SEC,
    LLM_ADAPTER,
    LLM_PROVIDER,
    select_llm_adapter,
)

__all__ = [
    "ANTHROPIC_ADAPTER",
    "ANTHROPIC_MAX_TOKENS",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_TIMEOUT_SEC",
    "LLM_ADAPTER",
    "LLM_PROVIDER",
    "select_llm_adapter",
]

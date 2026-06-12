"""Getrennte LLM-Call-Profile (Narrator/Extractor/Repair).

Jede Rolle kann per ENV ein eigenes Modell und num_ctx bekommen.
Unsesetzte Werte (None) fallen auf die Adapter-Defaults zurueck, das
Standardverhalten bleibt damit unveraendert.

ENV-Knöpfe:
  OLLAMA_NARRATOR_MODEL / OLLAMA_NARRATOR_NUM_CTX
  OLLAMA_EXTRACTOR_MODEL / OLLAMA_EXTRACTOR_NUM_CTX
  OLLAMA_REPAIR_MODEL / OLLAMA_REPAIR_NUM_CTX
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LlmCallProfile:
    model: Optional[str]
    num_ctx: Optional[int]


def _optional_str(name: str) -> Optional[str]:
    raw = str(os.getenv(name, "")).strip()
    return raw or None


def _optional_int(name: str) -> Optional[int]:
    raw = str(os.getenv(name, "")).strip()
    try:
        value = int(raw) if raw else 0
    except ValueError:
        return None
    return value if value > 0 else None


def narrator_profile() -> LlmCallProfile:
    return LlmCallProfile(model=_optional_str("OLLAMA_NARRATOR_MODEL"), num_ctx=_optional_int("OLLAMA_NARRATOR_NUM_CTX"))


def extractor_profile() -> LlmCallProfile:
    return LlmCallProfile(model=_optional_str("OLLAMA_EXTRACTOR_MODEL"), num_ctx=_optional_int("OLLAMA_EXTRACTOR_NUM_CTX"))


def repair_profile() -> LlmCallProfile:
    return LlmCallProfile(model=_optional_str("OLLAMA_REPAIR_MODEL"), num_ctx=_optional_int("OLLAMA_REPAIR_NUM_CTX"))

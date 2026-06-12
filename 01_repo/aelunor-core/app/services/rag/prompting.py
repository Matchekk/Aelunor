"""Prompt rendering for turn-scoped RAG context."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

_OPEN = "[RELEVANT CAMPAIGN MEMORY]"
_CLOSE = "[/RELEVANT CAMPAIGN MEMORY]"
_NOTE = (
    "Kontext, keine neuen Fakten: Bei Konflikten gewinnt immer der aktuelle "
    "strukturierte Campaign-State."
)


def _clip_line(value: Any, limit: int = 420) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 18)].rstrip() + " [... gekuerzt]"


def _render_chunk(chunk: Mapping[str, Any]) -> str:
    title = _clip_line(chunk.get("title") or chunk.get("id") or "Kontext", 120)
    chunk_type = _clip_line(chunk.get("type") or "unknown", 60)
    source = _clip_line(chunk.get("source_hint") or "", 120)
    score = chunk.get("score", 0.0)
    try:
        score_text = f"{float(score):.2f}"
    except (TypeError, ValueError):
        score_text = "0.00"
    prefix = f"- {chunk_type}: {title} (score {score_text}"
    prefix += f", source {source}" if source else ""
    prefix += ")"
    text = _clip_line(chunk.get("text") or "", 520)
    return prefix + (f"\n  {text}" if text else "")


def build_turn_rag_prompt_block(
    rag_context: Mapping[str, Any] | None,
    *,
    max_items: int = 6,
    max_chars: int = 3500,
) -> str:
    """Render top RAG chunks into a bounded narrator prompt block."""
    if not isinstance(rag_context, Mapping):
        return ""
    chunks = rag_context.get("chunks")
    if not isinstance(chunks, Sequence) or isinstance(chunks, (str, bytes)):
        return ""
    item_limit = max(0, int(max_items or 0))
    char_limit = max(0, int(max_chars or 0))
    if item_limit <= 0 or char_limit <= len(_OPEN) + len(_CLOSE) + 8:
        return ""

    body: list[str] = []
    for raw_chunk in chunks[:item_limit]:
        if not isinstance(raw_chunk, Mapping):
            continue
        entry = _render_chunk(raw_chunk)
        candidate = "\n".join([_OPEN, _NOTE, *body, entry, _CLOSE])
        if len(candidate) > char_limit:
            break
        body.append(entry)
    if not body:
        return ""
    return "\n".join([_OPEN, _NOTE, *body, _CLOSE])


__all__ = ["build_turn_rag_prompt_block"]

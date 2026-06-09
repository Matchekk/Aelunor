"""Internal, read-only helpers for ``document_mapping``.

Pure stdlib value coercion, container iteration and bounded text rendering.
Everything here is side-effect free and never mutates its input. Not part of
the public RAG surface (see ``__init__.py``).
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

MAX_LIST_ITEMS = 8
MAX_FACTS = 12


def text(value: Any) -> str:
    """Coerce only scalar text/number values to a stripped string."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def first_text(record: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        out = text(record.get(key))
        if out:
            return out
    return ""


def first_value(record: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value:
            return value
    return None


def dig(state: Any, path: Sequence[str]) -> Any:
    node = state
    for key in path:
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def dedupe(items: Sequence[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        item = item.strip()
        if item and item not in out:
            out.append(item)
    return out


def names(value: Any, limit: int = MAX_LIST_ITEMS) -> list[str]:
    """Extract display names from a list/dict/scalar of entities."""
    raw: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(item, Mapping):
                raw.append(first_text(item, ("name", "title", "id")) or text(key))
            else:
                raw.append(text(item) or text(key))
    elif isinstance(value, (list, tuple)):
        for item in value:
            raw.append(first_text(item, ("name", "title", "id"))
                       if isinstance(item, Mapping) else text(item))
    else:
        raw.append(text(value))
    return dedupe(raw)[:limit]


def facts(value: Any, limit: int = MAX_FACTS) -> list[str]:
    """Render a list/dict/scalar of facts into short bullet strings."""
    out: list[str] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            out.append(first_text(item, ("text", "fact", "summary", "name", "title"))
                       if isinstance(item, Mapping) else text(item))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            label, detail = text(key), text(item)
            out.append(f"{label}: {detail}" if label and detail else (detail or label))
    else:
        out.append(text(value))
    return dedupe(out)[:limit]


def render_text(*, title: str, type_label: str, status: str = "", summary: str = "",
                facts_lines: Optional[Sequence[str]] = None,
                related: Optional[Mapping[str, Sequence[str]]] = None,
                max_text_chars: int) -> str:
    """Render a compact, readable, bounded document body."""
    lines = [f"Title: {title}", f"Type: {type_label}"]
    if status:
        lines.append(f"Status: {status}")
    if summary:
        lines.append(f"Summary: {summary}")
    if facts_lines:
        lines.append("Facts:")
        lines.extend(f"- {fact}" for fact in facts_lines)
    related = related or {}
    related_lines = [f"- {label}: {', '.join(related[label])}"
                     for label in ("NPCs", "Locations", "Quests") if related.get(label)]
    if related_lines:
        lines.append("Related:")
        lines.extend(related_lines)
    body = "\n".join(lines)
    return body[:max_text_chars].rstrip() if len(body) > max_text_chars else body


def records(container: Any) -> list[tuple[Mapping[str, Any], str]]:
    """Yield (record, fallback_key) for dict (sorted) or list containers."""
    out: list[tuple[Mapping[str, Any], str]] = []
    if isinstance(container, Mapping):
        for key in sorted(container.keys(), key=lambda k: str(k)):
            if isinstance(container[key], Mapping):
                out.append((container[key], str(key)))
    elif isinstance(container, (list, tuple)):
        for index, value in enumerate(container):
            if isinstance(value, Mapping):
                out.append((value, str(index)))
    return out


def first_container(state: Mapping[str, Any], paths: Sequence[Sequence[str]]) -> Any:
    for path in paths:
        node = dig(state, path)
        if isinstance(node, (Mapping, list, tuple)) and node:
            return node
    return None


def merged_text(sources: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str:
    for source in sources:
        out = first_text(source, keys)
        if out:
            return out
    return ""

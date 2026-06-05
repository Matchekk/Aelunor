from __future__ import annotations

from typing import Any, Dict, List

from app.config.runtime import EXTRACTION_QUARANTINE_DEFAULT_MAX, EXTRACTION_REASON_LOW_CONFIDENCE
from app.core.ids import deep_copy, make_id, utc_now
from app.services.world.math_utils import clamp
from app.services.world.text_normalization import normalized_eval_text

def default_extraction_quarantine() -> Dict[str, Any]:
    return {
        "entries": [],
        "max_entries": EXTRACTION_QUARANTINE_DEFAULT_MAX,
    }

def normalize_extraction_quarantine_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    raw = meta.get("extraction_quarantine")
    quarantine = deep_copy(raw) if isinstance(raw, dict) else default_extraction_quarantine()
    max_entries = int(quarantine.get("max_entries", EXTRACTION_QUARANTINE_DEFAULT_MAX) or EXTRACTION_QUARANTINE_DEFAULT_MAX)
    max_entries = clamp(max_entries, 1, 1000)
    entries: List[Dict[str, Any]] = []
    for raw_entry in (quarantine.get("entries") or []):
        if not isinstance(raw_entry, dict):
            continue
        status = str(raw_entry.get("status") or "").strip().lower()
        if status not in {"review", "reject"}:
            continue
        normalized_entry = {
            "id": str(raw_entry.get("id") or make_id("xq")).strip(),
            "turn": max(0, int(raw_entry.get("turn", 0) or 0)),
            "actor": str(raw_entry.get("actor") or "").strip(),
            "source": str(raw_entry.get("source") or "unknown").strip(),
            "entity_type": str(raw_entry.get("entity_type") or "unknown").strip(),
            "status": status,
            "reason_code": str(raw_entry.get("reason_code") or EXTRACTION_REASON_LOW_CONFIDENCE).strip(),
            "label": str(raw_entry.get("label") or "").strip(),
            "payload": deep_copy(raw_entry.get("payload") or {}),
            "created_at": str(raw_entry.get("created_at") or utc_now()),
        }
        entries.append(normalized_entry)
    if len(entries) > max_entries:
        entries = entries[-max_entries:]
    normalized = {"entries": entries, "max_entries": max_entries}
    meta["extraction_quarantine"] = normalized
    return normalized

def append_extraction_quarantine(state: Dict[str, Any], candidates_review_reject: List[Dict[str, Any]]) -> None:
    if not candidates_review_reject:
        return
    meta = state.setdefault("meta", {})
    quarantine = normalize_extraction_quarantine_meta(meta)
    entries = quarantine.setdefault("entries", [])
    seen = {
        (
            int(entry.get("turn", 0) or 0),
            str(entry.get("actor") or ""),
            str(entry.get("source") or ""),
            str(entry.get("entity_type") or ""),
            normalized_eval_text(entry.get("label", "")),
            str(entry.get("reason_code") or ""),
        )
        for entry in entries
        if isinstance(entry, dict)
    }
    for candidate in candidates_review_reject:
        status = str(candidate.get("status") or "").strip().lower()
        if status not in {"review", "reject"}:
            continue
        key = (
            int(candidate.get("turn", 0) or 0),
            str(candidate.get("actor") or ""),
            str(candidate.get("source") or ""),
            str(candidate.get("entity_type") or ""),
            normalized_eval_text(candidate.get("label", "")),
            str(candidate.get("reason_code") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "id": make_id("xq"),
                "turn": max(0, int(candidate.get("turn", 0) or 0)),
                "actor": str(candidate.get("actor") or "").strip(),
                "source": str(candidate.get("source") or "unknown").strip(),
                "entity_type": str(candidate.get("entity_type") or "unknown").strip(),
                "status": status,
                "reason_code": str(candidate.get("reason_code") or EXTRACTION_REASON_LOW_CONFIDENCE).strip(),
                "label": str(candidate.get("label") or "").strip(),
                "payload": deep_copy(candidate.get("payload") or {}),
                "created_at": str(candidate.get("created_at") or utc_now()),
            }
        )
    max_entries = int(quarantine.get("max_entries", EXTRACTION_QUARANTINE_DEFAULT_MAX) or EXTRACTION_QUARANTINE_DEFAULT_MAX)
    if len(entries) > max_entries:
        quarantine["entries"] = entries[-max_entries:]

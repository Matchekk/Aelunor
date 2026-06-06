"""Normalize plotpoint and event board entries.

Pure board-domain logic extracted from the state runtime core.
"""
import json
from typing import Any, Dict, Optional

from app.core.ids import deep_copy, make_id


def normalize_plotpoint_entry(raw: Any) -> Optional[Dict[str, Any]]:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        return {
            "id": make_id("pp"),
            "type": "story",
            "title": text[:120],
            "status": "active",
            "owner": None,
            "notes": text,
            "requirements": [],
        }
    if not isinstance(raw, dict):
        return None
    plotpoint = deep_copy(raw)
    pid = str(plotpoint.get("id") or plotpoint.get("point_id") or plotpoint.get("entry_id") or make_id("pp")).strip()
    title = str(plotpoint.get("title") or plotpoint.get("name") or plotpoint.get("description") or pid).strip()
    notes = str(plotpoint.get("notes") or plotpoint.get("description") or plotpoint.get("content") or "").strip()
    status = str(plotpoint.get("status") or "active").strip().lower()
    if status not in {"active", "done", "failed"}:
        status = "active"
    owner = str(plotpoint.get("owner") or "").strip() or None
    requirements = [str(entry).strip() for entry in (plotpoint.get("requirements") or []) if str(entry).strip()]
    normalized = {
        **plotpoint,
        "id": pid,
        "type": str(plotpoint.get("type") or "story").strip() or "story",
        "title": title or pid,
        "status": status,
        "owner": owner,
        "notes": notes,
        "requirements": requirements,
    }
    return normalized


def normalize_plotpoint_update_entry(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    pid = str(raw.get("id") or raw.get("point_id") or raw.get("entry_id") or "").strip()
    if not pid:
        return None
    normalized: Dict[str, Any] = {"id": pid}
    if raw.get("status"):
        status = str(raw.get("status") or "").strip().lower()
        if status in {"active", "done", "failed"}:
            normalized["status"] = status
    notes = str(raw.get("notes") or raw.get("description") or raw.get("content") or "").strip()
    if notes:
        normalized["notes"] = notes
    return normalized


def normalize_event_entry(raw: Any) -> Optional[str]:
    if isinstance(raw, str):
        text = raw.strip()
        return text or None
    if isinstance(raw, dict):
        for key in ("text", "detail", "description", "content", "title", "name", "event"):
            text = str(raw.get(key) or "").strip()
            if text:
                return text
        return json.dumps(raw, ensure_ascii=False)[:300]
    text = str(raw or "").strip()
    return text or None

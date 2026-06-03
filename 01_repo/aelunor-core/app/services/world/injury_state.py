"""Injury and scar state normalization helpers for world state."""

from typing import Any, Dict, Optional


def default_injury_state() -> Dict[str, Any]:
    return {
        "id": "",
        "title": "",
        "severity": "leicht",
        "effects": [],
        "healing_stage": "frisch",
        "will_scar": False,
        "created_turn": 0,
        "notes": "",
    }


def default_scar_state() -> Dict[str, Any]:
    return {
        "id": "",
        "title": "",
        "origin_injury_id": None,
        "description": "",
        "created_turn": 0,
    }


def normalize_injury_state(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    injury = default_injury_state()
    injury.update(deep_copy(value))
    injury["id"] = str(injury.get("id") or make_id("inj")).strip()
    injury["title"] = str(injury.get("title") or "").strip()
    if not injury["title"]:
        return None
    injury["severity"] = str(injury.get("severity") or "leicht").strip().lower()
    if injury["severity"] not in INJURY_SEVERITIES:
        injury["severity"] = "leicht"
    injury["effects"] = [str(entry).strip() for entry in (injury.get("effects") or []) if str(entry).strip()]
    injury["healing_stage"] = str(injury.get("healing_stage") or "frisch").strip().lower()
    if injury["healing_stage"] not in INJURY_HEALING_STAGES:
        injury["healing_stage"] = "frisch"
    injury["will_scar"] = bool(injury.get("will_scar", False))
    injury["created_turn"] = max(0, int(injury.get("created_turn", 0) or 0))
    injury["notes"] = str(injury.get("notes") or "").strip()
    return injury


def normalize_scar_state(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    scar = default_scar_state()
    scar.update(deep_copy(value))
    scar["id"] = str(scar.get("id") or make_id("scar")).strip()
    scar["title"] = str(scar.get("title") or scar.get("label") or "").strip()
    if not scar["title"]:
        return None
    scar["origin_injury_id"] = str(scar.get("origin_injury_id") or "").strip() or None
    scar["description"] = str(scar.get("description") or scar.get("source") or scar["title"]).strip()
    scar["created_turn"] = max(0, int(scar.get("created_turn") or scar.get("turn_number") or 0))
    return scar

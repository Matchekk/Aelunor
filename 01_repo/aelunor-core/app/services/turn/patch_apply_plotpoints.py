from typing import Any, Callable, Dict, Optional


def apply_patch_plotpoint_updates(
    state: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    normalize_plotpoint_entry: Callable[[Any], Optional[Dict[str, Any]]],
    normalize_plotpoint_update_entry: Callable[[Any], Optional[Dict[str, Any]]],
) -> None:
    state["plotpoints"] = [
        entry
        for entry in (normalize_plotpoint_entry(raw) for raw in (state.get("plotpoints") or []))
        if entry
    ]
    for raw_pp in (patch.get("plotpoints_add") or []):
        pp = normalize_plotpoint_entry(raw_pp)
        if not pp:
            continue
        if not any(isinstance(existing, dict) and existing.get("id") == pp.get("id") for existing in state["plotpoints"]):
            state["plotpoints"].append(pp)

    for raw_upd in (patch.get("plotpoints_update") or []):
        upd = normalize_plotpoint_update_entry(raw_upd)
        if not upd:
            continue
        pid = upd.get("id")
        for pp in state["plotpoints"]:
            if isinstance(pp, dict) and pp.get("id") == pid:
                if "status" in upd:
                    pp["status"] = upd["status"]
                if "notes" in upd and upd["notes"]:
                    pp["notes"] = upd["notes"]

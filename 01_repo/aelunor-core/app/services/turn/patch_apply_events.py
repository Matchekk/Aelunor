from typing import Any, Callable, Dict, Optional


def apply_patch_event_updates(
    state: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    normalize_event_entry: Callable[[Any], Optional[str]],
) -> None:
    state.setdefault("events", [])
    for entry in (normalize_event_entry(raw) for raw in (patch.get("events_add") or [])):
        if entry:
            state["events"].append(entry)

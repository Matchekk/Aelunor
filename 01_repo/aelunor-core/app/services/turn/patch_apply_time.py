from typing import Any, Callable, Dict, Optional


def apply_patch_time_advance(
    state: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    apply_world_time_advance: Callable[[Dict[str, Any], int, Optional[str]], None],
) -> None:
    time_advance = ((patch.get("meta") or {}).get("time_advance") or {})
    if time_advance:
        apply_world_time_advance(state, int(time_advance.get("days", 0) or 0), time_advance.get("time_of_day"))
        if time_advance.get("reason"):
            state.setdefault("events", [])
            state["events"].append(f"Zeit vergeht: +{int(time_advance.get('days', 0) or 0)} Tage ({time_advance.get('reason')}).")

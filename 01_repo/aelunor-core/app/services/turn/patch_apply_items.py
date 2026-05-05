from typing import Any, Callable, Dict


def apply_patch_item_updates(
    state: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    ensure_item_shape: Callable[[str, Dict[str, Any]], Dict[str, Any]],
) -> None:
    state.setdefault("items", {})
    for item_id, item in (patch.get("items_new") or {}).items():
        state["items"][item_id] = ensure_item_shape(item_id, item)

from typing import Any, Dict


def apply_patch_meta_updates(state: Dict[str, Any], patch: Dict[str, Any]) -> None:
    meta = patch.get("meta")
    if meta and "phase" in meta:
        state["meta"]["phase"] = meta["phase"]

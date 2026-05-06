from typing import Any, Dict


def apply_patch_character_bio_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
) -> None:
    if "scene_id" in upd:
        character["scene_id"] = upd.get("scene_id", character.get("scene_id"))
    if upd.get("bio_set"):
        character["bio"] = {**character.get("bio", {}), **upd["bio_set"]}
        character["bio"].pop("party_role", None)

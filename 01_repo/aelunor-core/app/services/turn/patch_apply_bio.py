from typing import Any, Dict


def apply_patch_character_bio_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
) -> None:
    if "scene_id" in upd:
        character["scene_id"] = upd.get("scene_id", character.get("scene_id"))
    bio_set = upd.get("bio_set")
    if isinstance(bio_set, dict) and bio_set:
        base_bio = character.get("bio") if isinstance(character.get("bio"), dict) else {}
        character["bio"] = {**base_bio, **bio_set}
        character["bio"].pop("party_role", None)

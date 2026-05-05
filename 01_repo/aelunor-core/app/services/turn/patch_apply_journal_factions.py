from typing import Any, Callable, Dict


def apply_patch_character_journal_faction_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    *,
    deep_copy: Callable[[Any], Any],
    include_journal: bool = True,
    include_factions: bool = True,
) -> None:
    if include_journal and upd.get("journal_add"):
        journal = character.setdefault("journal", {})
        for key, value in upd["journal_add"].items():
            journal.setdefault(key, [])
            if isinstance(value, list):
                journal[key].extend(value)

    if include_factions:
        for faction in upd.get("factions_add", []) or []:
            faction_id = faction.get("faction_id", "")
            if not faction_id:
                continue
            memberships = character.setdefault("faction_memberships", [])
            existing = next((entry for entry in memberships if entry.get("faction_id") == faction_id), None)
            if existing:
                existing.update(deep_copy(faction))
            else:
                memberships.append(deep_copy(faction))
        for faction_update in upd.get("factions_update", []) or []:
            faction_id = faction_update.get("faction_id", "")
            for membership in character.setdefault("faction_memberships", []):
                if membership.get("faction_id") == faction_id:
                    membership.update(deep_copy(faction_update))
                    break

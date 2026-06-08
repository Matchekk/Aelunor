from typing import Any, Callable, Dict


def apply_patch_character_journal_faction_updates(
    character: Dict[str, Any],
    upd: Dict[str, Any],
    *,
    deep_copy: Callable[[Any], Any],
    include_journal: bool = True,
    include_factions: bool = True,
) -> None:
    journal_add = upd.get("journal_add")
    if include_journal and isinstance(journal_add, dict) and journal_add:
        journal = character.get("journal")
        if not isinstance(journal, dict):
            journal = {}
            character["journal"] = journal
        for key, value in journal_add.items():
            if not isinstance(journal.get(key), list):
                journal[key] = []
            if isinstance(value, list):
                journal[key].extend(value)

    if include_factions:
        for faction in upd.get("factions_add", []) or []:
            if not isinstance(faction, dict):
                continue
            faction_id = faction.get("faction_id", "")
            if not faction_id:
                continue
            memberships = character.setdefault("faction_memberships", [])
            existing = next((entry for entry in memberships if isinstance(entry, dict) and entry.get("faction_id") == faction_id), None)
            if existing:
                existing.update(deep_copy(faction))
            else:
                memberships.append(deep_copy(faction))
        for faction_update in upd.get("factions_update", []) or []:
            if not isinstance(faction_update, dict):
                continue
            faction_id = faction_update.get("faction_id", "")
            for membership in character.setdefault("faction_memberships", []):
                if isinstance(membership, dict) and membership.get("faction_id") == faction_id:
                    membership.update(deep_copy(faction_update))
                    break

import hashlib


def appearance_event_id(slot_name: str, kind: str, source: str, turn_number: int, absolute_day: int, new_value: str) -> str:
    digest = hashlib.sha256(f"{slot_name}:{kind}:{source}:{turn_number}:{absolute_day}:{new_value}".encode("utf-8")).hexdigest()[:10]
    return f"app_{digest}"


def format_appearance_message(display_name: str, kind: str, source: str, new_value: str) -> str:
    if kind == "aging_stage":
        return f"{display_name} wirkt nun deutlich {new_value}."
    if kind == "corruption_threshold":
        return f"An {display_name} wird die Verderbnis sichtbar: {new_value}."
    if kind == "class_visual":
        return f"{display_name}s neue Klasse hinterlässt sichtbare Spuren: {new_value}."
    if kind == "faction_visual":
        return f"{display_name} trägt nun sichtbare Zeichen einer Fraktion: {new_value}."
    if kind == "scar_added":
        return f"{display_name} trägt nun eine neue Narbe: {new_value}."
    return f"{display_name}s Erscheinung verändert sich: {new_value}."


def record_appearance_change(
    character: dict,
    *,
    slot_name: str,
    turn_number: int,
    absolute_day: int,
    kind: str,
    source: str,
    old_value: str,
    new_value: str,
) -> dict | None:
    if old_value == new_value:
        return None
    display_name = (character.get("bio") or {}).get("name") or slot_name
    event_id = appearance_event_id(slot_name, kind, source, turn_number, absolute_day, new_value)
    if any(entry.get("event_id") == event_id for entry in (character.get("appearance_history") or [])):
        return None
    event = {
        "event_id": event_id,
        "absolute_day": absolute_day,
        "turn_number": turn_number,
        "kind": kind,
        "source": source,
        "old_value": old_value,
        "new_value": new_value,
        "message": format_appearance_message(display_name, kind, source, new_value),
    }
    character.setdefault("appearance_history", []).append(event)
    return event


def active_faction_ids(character: dict) -> set:
    return {entry.get("faction_id") for entry in (character.get("faction_memberships") or []) if entry.get("active", True)}

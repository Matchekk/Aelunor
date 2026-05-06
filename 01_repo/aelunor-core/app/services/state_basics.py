import re
import secrets
from typing import Any, Dict, List


def make_join_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def slot_id(index: int, *, slot_prefix: str) -> str:
    return f"{slot_prefix}{index}"


def slot_index(value: str, *, slot_prefix: str) -> int:
    if not value.startswith(slot_prefix):
        return 9999
    try:
        return int(value.split("_", 1)[1])
    except (IndexError, ValueError):
        return 9999


def is_slot_id(value: str) -> bool:
    return bool(re.fullmatch(r"slot_[1-9]\d*", value or ""))


def ordered_slots(keys: List[str], *, slot_prefix: str) -> List[str]:
    return sorted(keys, key=lambda key: slot_index(key, slot_prefix=slot_prefix))


def blank_patch() -> Dict[str, Any]:
    return {
        "meta": {},
        "characters": {},
        "items_new": {},
        "plotpoints_add": [],
        "plotpoints_update": [],
        "map_add_nodes": [],
        "map_add_edges": [],
        "events_add": [],
    }

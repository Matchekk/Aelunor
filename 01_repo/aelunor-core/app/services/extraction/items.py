from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from app.core.ids import make_id
from app.services.campaigns.party import display_name_for_slot
from app.services.campaigns.views import active_turns
from app.services.characters.resource_maxima import iter_equipped_item_ids, list_inventory_items
from app.services.items.inventory import ensure_item_shape
from app.services.setup.answers import parse_earth_items, summarize_creator_item_name
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import (
    AUTO_ITEM_ACQUIRE_PATTERNS,
    AUTO_ITEM_EQUIP_PATTERNS,
    AUTO_ITEM_GENERIC_NAMES,
    ITEM_CHEST_KEYWORDS,
    ITEM_DETAIL_CLAUSE_MARKERS,
    ITEM_OFFHAND_KEYWORDS,
    ITEM_TRINKET_KEYWORDS,
    ITEM_WEAPON_KEYWORDS,
)


def sentence_mentions_actor_name(sentence: str, actor_display: str) -> bool:
    normalized_sentence = normalized_eval_text(sentence)
    actor_name = normalized_eval_text(actor_display)
    if not normalized_sentence or not actor_name:
        return False
    if actor_name in normalized_sentence:
        return True
    actor_tokens = [token for token in actor_name.split() if len(token) >= 4]
    sentence_tokens = [token.strip(".,:;!?()[]{}\"'") for token in normalized_sentence.split() if len(token.strip(".,:;!?()[]{}\"'")) >= 4]
    for actor_token in actor_tokens[:2]:
        for sentence_token in sentence_tokens[:4]:
            if sentence_token.startswith(actor_token) or actor_token.startswith(sentence_token):
                return True
            if SequenceMatcher(None, actor_token, sentence_token).ratio() >= 0.72:
                return True
    return False


def clean_auto_item_name(raw_name: str) -> str:
    name = str(raw_name or "").replace("\n", " ").strip().strip(".,:;!?\"“”„' ")
    name = re.sub(r"^\s*\d+[\.\)]\s*", "", name)
    name = re.sub(r"^(?:die|der|das|ein|eine|einen|einem)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(?:mein(?:e|en|em|er)?|dein(?:e|en|em|er)?|sein(?:e|en|em|er)?|ihr(?:e|en|em|er)?)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+aus\s+der\s+scheide\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+vor\s+(?:mich|ihn|sie|ihm|ihr|sich|uns|euch)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:und|aber|doch|wobei|wodurch|als|während)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\([^)]{0,120}\)", "", name)
    lowered = f" {normalized_eval_text(name)} "
    for marker in ITEM_DETAIL_CLAUSE_MARKERS:
        idx = lowered.find(marker)
        if idx > 6:
            name = name[: idx - 1].strip()
            break
    name = re.sub(r"\s+", " ", name).strip(" -")
    normalized = normalized_eval_text(name)
    if not name or normalized in AUTO_ITEM_GENERIC_NAMES:
        return ""
    if len(name) < 3:
        return ""
    words = name.split()
    if len(words) > 7:
        name = " ".join(words[:7]).strip()
        normalized = normalized_eval_text(name)
    if not re.search(r"[A-Za-zÄÖÜäöüß]", name):
        return ""
    if normalized in AUTO_ITEM_GENERIC_NAMES:
        return ""
    return name[:80].strip(" ,-.")

def actor_relevant_story_sentences(story_text: str, actor_display: str) -> List[str]:
    actor_name = normalized_eval_text(actor_display)
    relevant: List[str] = []
    actor_subject_active = False
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(story_text or "")):
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized_sentence = normalized_eval_text(sentence)
        starts_pronoun = normalized_sentence.startswith(("er ", "sie ", "es ", "ihn ", "ihm ", "ihr "))
        starts_first_person = normalized_sentence.startswith(
            ("ich ", "mich ", "mir ", "mein ", "meine ", "meinen ", "meinem ", "meiner ")
        )
        if starts_first_person:
            actor_subject_active = True
            relevant.append(sentence)
            continue
        if actor_name and sentence_mentions_actor_name(sentence, actor_display):
            actor_subject_active = True
            relevant.append(sentence)
            continue
        if starts_pronoun and actor_subject_active:
            relevant.append(sentence)
            continue
        if actor_subject_active and normalized_sentence.startswith(
            ("dann ", "danach ", "darauf ", "anschließend ", "anschliessend ", "nun ", "jetzt ")
        ):
            relevant.append(sentence)
            continue
        actor_subject_active = False
    return relevant

def infer_item_slot_from_text(item_name: str, sentence: str) -> str:
    lowered_name = normalized_eval_text(item_name)
    lowered_sentence = normalized_eval_text(sentence)
    if any(keyword in lowered_name for keyword in ITEM_OFFHAND_KEYWORDS):
        return "offhand"
    if any(keyword in lowered_name for keyword in ITEM_CHEST_KEYWORDS):
        return "chest"
    if any(keyword in lowered_name for keyword in ITEM_TRINKET_KEYWORDS):
        return "trinket"
    if any(keyword in lowered_name for keyword in ITEM_WEAPON_KEYWORDS):
        return "weapon"
    if any(keyword in lowered_sentence for keyword in ITEM_OFFHAND_KEYWORDS):
        return "offhand"
    if any(keyword in lowered_sentence for keyword in ITEM_CHEST_KEYWORDS):
        return "chest"
    if any(keyword in lowered_sentence for keyword in ITEM_TRINKET_KEYWORDS):
        return "trinket"
    if any(keyword in lowered_sentence for keyword in ITEM_WEAPON_KEYWORDS):
        return "weapon"
    if any(marker in lowered_sentence for marker in (" in der hand", " schwingt ", " zieht ", " fuehrt ", " führt ")):
        return "weapon"
    return ""

def build_auto_item_stub(item_name: str, sentence: str) -> Dict[str, Any]:
    lowered = normalized_eval_text(f"{item_name} {sentence}")
    slot = infer_item_slot_from_text(item_name, sentence)
    tags = ["story_auto", "auto_item"]
    weapon_profile: Dict[str, Any] = {}
    if slot == "weapon":
        tags.append("weapon")
        category = "ranged" if any(marker in lowered for marker in ("bogen", "armbrust")) else "melee"
        scaling_stat = "dex" if category == "ranged" else "str"
        if any(marker in lowered for marker in ("stab", "rune", "fokus", "orb")):
            scaling_stat = "int"
        weapon_profile = {"category": category, "scaling_stat": scaling_stat, "damage_min": 1, "damage_max": 3, "attack_bonus": 0}
    elif slot == "offhand":
        tags.append("offhand")
    elif slot == "chest":
        tags.append("armor")
    elif slot == "trinket":
        tags.append("trinket")
    return {"slot": slot, "tags": list(dict.fromkeys(tags)), "weapon_profile": weapon_profile}

def clean_creator_item_name(raw_name: str) -> str:
    name = summarize_creator_item_name(raw_name)
    name = str(name or "").strip().strip(".,:;!?\"“”„' ")
    name = re.sub(r"^(?:die|der|das|ein|eine|einen|einem)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(" -")
    if len(name) < 3:
        return ""
    return name[:140]

def item_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_eval_text(name)).strip("-")
    slug = slug[:36] or make_id("item")
    return f"item_{slug}"

def materialize_inventory_item(
    state: Dict[str, Any],
    character: Dict[str, Any],
    item_name: str,
    *,
    source_tag: str,
    item_id: Optional[str] = None,
) -> Optional[str]:
    clean_name = (
        clean_creator_item_name(item_name)
        if source_tag in {"signature_item", "earth_origin"}
        else clean_auto_item_name(item_name)
    )
    if not clean_name:
        return None
    items_db = state.setdefault("items", {})
    inventory = character.setdefault("inventory", {})
    inventory_items = inventory.setdefault("items", [])
    existing_ids = {entry.get("item_id") for entry in list_inventory_items(character)}
    known_names = {
        normalized_eval_text((items_db.get(existing_id, {}) or {}).get("name", ""))
        for existing_id in existing_ids
        if existing_id
    }
    normalized_name = normalized_eval_text(clean_name)
    if normalized_name in known_names:
        return None

    target_item_id = item_id or item_id_from_name(clean_name)
    suffix = 2
    while target_item_id in items_db and normalized_eval_text((items_db.get(target_item_id, {}) or {}).get("name", "")) != normalized_name:
        target_item_id = f"{item_id_from_name(clean_name)}-{suffix}"
        suffix += 1

    items_db[target_item_id] = ensure_item_shape(
        target_item_id,
        {
            "name": clean_name[0].upper() + clean_name[1:] if clean_name else clean_name,
            "rarity": "common",
            "slot": "",
            "weight": 1,
            "stackable": False,
            "max_stack": 1,
            "weapon_profile": {},
            "modifiers": [],
            "effects": [],
            "durability": {"current": 100, "max": 100},
            "cursed": False,
            "curse_text": "",
            "tags": [source_tag],
        },
    )
    if target_item_id not in existing_ids:
        inventory_items.append({"item_id": target_item_id, "stack": 1})
    return target_item_id

def normalize_creator_item_list(value: Any) -> List[str]:
    if isinstance(value, list):
        joined = "\n".join(str(entry or "") for entry in value if str(entry or "").strip())
        return parse_earth_items(joined)
    return parse_earth_items(str(value or ""))

def reconcile_creator_inventory_items(state: Dict[str, Any], character: Dict[str, Any]) -> None:
    items_db = state.setdefault("items", {})
    inventory = character.setdefault("inventory", {})
    inventory_items = inventory.setdefault("items", [])
    creator_item_ids = {
        entry.get("item_id")
        for entry in inventory_items
        if entry.get("item_id") and any(
            tag in {"earth_origin", "signature_item"}
            for tag in ((items_db.get(entry.get("item_id"), {}) or {}).get("tags") or [])
        )
    }
    if creator_item_ids:
        inventory["items"] = [entry for entry in inventory_items if entry.get("item_id") not in creator_item_ids]

    bio = character.setdefault("bio", {})
    bio["earth_items"] = normalize_creator_item_list(bio.get("earth_items", []))
    bio["signature_item"] = clean_creator_item_name(bio.get("signature_item", ""))

    materialize_inventory_item(state, character, bio.get("signature_item", ""), source_tag="signature_item")
    for earth_item in bio.get("earth_items", []) or []:
        materialize_inventory_item(state, character, earth_item, source_tag="earth_origin")

def extract_auto_story_item_events(story_text: str, actor_display: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    by_name: Dict[str, Dict[str, Any]] = {}
    for sentence in actor_relevant_story_sentences(story_text, actor_display):
        for pattern in AUTO_ITEM_ACQUIRE_PATTERNS:
            for match in pattern.findall(sentence):
                item_name = clean_auto_item_name(match)
                normalized_name = normalized_eval_text(item_name)
                if not item_name or not normalized_name:
                    continue
                if normalized_name not in by_name:
                    event = {"name": item_name, "mode": "acquire", "sentence": sentence}
                    by_name[normalized_name] = event
                    events.append(event)
                if len(events) >= 3:
                    return events
        for pattern in AUTO_ITEM_EQUIP_PATTERNS:
            for match in pattern.findall(sentence):
                item_name = clean_auto_item_name(match)
                normalized_name = normalized_eval_text(item_name)
                if not item_name or not normalized_name:
                    continue
                if normalized_name in by_name:
                    by_name[normalized_name]["mode"] = "equip"
                    by_name[normalized_name]["sentence"] = sentence
                    continue
                event = {"name": item_name, "mode": "equip", "sentence": sentence}
                by_name[normalized_name] = event
                events.append(event)
                if len(events) >= 3:
                    return events
    return events

def extract_auto_story_items(story_text: str, actor_display: str) -> List[str]:
    return [event.get("name", "") for event in extract_auto_story_item_events(story_text, actor_display) if event.get("name")]

def inject_story_items(
    campaign: Dict[str, Any],
    working_state: Dict[str, Any],
    actor: str,
    story_text: str,
    patch: Dict[str, Any],
) -> Dict[str, Any]:
    if actor not in (working_state.get("characters") or {}):
        return patch
    actor_display = display_name_for_slot(campaign, actor)
    events = extract_auto_story_item_events(story_text, actor_display)
    if not events:
        return patch

    items_new = patch.setdefault("items_new", {})
    target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
    target_patch.setdefault("inventory_add", [])
    target_patch.setdefault("equipment_set", {})
    state_items = working_state.get("items", {}) or {}
    character = (working_state.get("characters", {}) or {}).get(actor, {})
    existing_ids = {entry.get("item_id") for entry in list_inventory_items(character)} | set(iter_equipped_item_ids(character))
    existing_names = {
        normalized_eval_text((state_items.get(item_id, {}) or {}).get("name", ""))
        for item_id in existing_ids
        if item_id
    }
    existing_names.update(
        normalized_eval_text((item or {}).get("name", ""))
        for item in items_new.values()
        if isinstance(item, dict) and item.get("name")
    )

    for event in events:
        item_name = str(event.get("name") or "").strip()
        if not item_name:
            continue
        normalized_name = normalized_eval_text(item_name)
        if not normalized_name or normalized_name in existing_names:
            existing_item_id = next(
                (
                    item_id
                    for item_id, item in {**state_items, **items_new}.items()
                    if normalized_eval_text((item or {}).get("name", "")) == normalized_name
                ),
                "",
            )
            if existing_item_id and str(event.get("mode") or "") == "equip":
                item_stub = build_auto_item_stub(item_name, str(event.get("sentence") or ""))
                equip_slot = item_stub.get("slot") or "weapon"
                target_patch["equipment_set"].setdefault(equip_slot, existing_item_id)
            continue
        existing_names.add(normalized_name)
        item_id = item_id_from_name(item_name)
        suffix = 2
        while item_id in state_items or item_id in items_new:
            known = state_items.get(item_id) or items_new.get(item_id) or {}
            if normalized_eval_text(known.get("name", "")) == normalized_name:
                break
            item_id = f"{item_id_from_name(item_name)}-{suffix}"
            suffix += 1
        item_stub = build_auto_item_stub(item_name, str(event.get("sentence") or ""))
        items_new[item_id] = ensure_item_shape(
            item_id,
            {
                "name": item_name[0].upper() + item_name[1:] if item_name else item_name,
                "rarity": "common",
                "slot": item_stub.get("slot", ""),
                "weight": 1,
                "stackable": False,
                "max_stack": 1,
                "weapon_profile": item_stub.get("weapon_profile", {}),
                "modifiers": [],
                "effects": [],
                "durability": {"current": 100, "max": 100},
                "cursed": False,
                "curse_text": "",
                "tags": item_stub.get("tags", ["story_auto", "auto_item"]),
            },
        )
        if item_id not in target_patch["inventory_add"]:
            target_patch["inventory_add"].append(item_id)
        if str(event.get("mode") or "") == "equip":
            equip_slot = item_stub.get("slot") or "weapon"
            target_patch["equipment_set"].setdefault(equip_slot, item_id)
    if not target_patch.get("equipment_set"):
        target_patch.pop("equipment_set", None)
    return patch

def materialize_story_items_from_turn_history(campaign: Dict[str, Any]) -> None:
    state = campaign.get("state", {}) or {}
    characters = state.get("characters", {}) or {}
    if not characters:
        return
    recent_turns = active_turns(campaign)[-12:]
    for turn in recent_turns:
        slot_name = turn.get("actor")
        if slot_name not in characters:
            continue
        character = characters.get(slot_name) or {}
        actor_display = display_name_for_slot(campaign, slot_name)
        for source_text in (
            turn.get("gm_text_display", ""),
            turn.get("input_text_display", "") if turn.get("action_type") in {"story", "canon"} else "",
        ):
            for event in extract_auto_story_item_events(source_text, actor_display):
                item_id = materialize_inventory_item(state, character, event.get("name", ""), source_tag="story_auto")
                if not item_id:
                    continue
                if str(event.get("mode") or "") != "equip":
                    continue
                item_stub = build_auto_item_stub(str(event.get("name") or ""), str(event.get("sentence") or ""))
                equip_slot = item_stub.get("slot") or "weapon"
                character.setdefault("equipment", {})[equip_slot] = item_id

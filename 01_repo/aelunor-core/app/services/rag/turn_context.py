"""Turn-scoped deterministic RAG context collector."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .chunking import chunk_document
from .models import RAGDocument, RetrievalQuery
from .retrieval import retrieve_chunks

_MAX_DOC_TEXT_CHARS = 1400
_MAX_RECENT_TURNS = 8
_SOURCE_HINT_KEY = "source_hint"


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def _render_value(value: Any) -> str:
    scalar = _text(value)
    if scalar:
        return scalar
    if isinstance(value, (Mapping, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            return ""
    return ""


def _join(parts: Sequence[Any], separator: str = " ") -> str:
    return separator.join(part for part in (_render_value(part) for part in parts) if part)


def _clip(text: Any, limit: int = _MAX_DOC_TEXT_CHARS) -> str:
    cleaned = " ".join(_render_value(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 18)].rstrip() + " [... gekuerzt]"


def _campaign_id(campaign: Mapping[str, Any]) -> str:
    meta = campaign.get("campaign_meta")
    if isinstance(meta, Mapping):
        value = _text(meta.get("campaign_id"))
        if value:
            return value
    return _text(campaign.get("campaign_id")) or "campaign"


def _doc(campaign_id: str, source_type: str, stable_key: Any, title: str, text: str,
         source_hint: str, *, salience: float = 0.5, metadata: Mapping[str, Any] | None = None) -> RAGDocument | None:
    body = _clip(text)
    if not body:
        return None
    safe_key = _text(stable_key) or source_type
    meta = dict(metadata or {})
    meta.update({"title": title or safe_key, _SOURCE_HINT_KEY: source_hint})
    return RAGDocument(
        id=f"{campaign_id}:turn_rag:{source_type}:{safe_key}",
        campaign_id=campaign_id,
        source_type=source_type,
        text=body,
        metadata=meta,
        salience=salience,
        canonical=True,
    )


def _character_name(slot: str, character: Mapping[str, Any]) -> str:
    bio = character.get("bio") if isinstance(character.get("bio"), Mapping) else {}
    profile = character.get("living_profile") if isinstance(character.get("living_profile"), Mapping) else {}
    identity = profile.get("identity") if isinstance(profile.get("identity"), Mapping) else {}
    return _text(identity.get("name")) or _text(bio.get("name")) or slot


def _character_docs(campaign_id: str, state: Mapping[str, Any]) -> list[RAGDocument]:
    docs: list[RAGDocument] = []
    characters = state.get("characters") if isinstance(state.get("characters"), Mapping) else {}
    items = state.get("items") if isinstance(state.get("items"), Mapping) else {}
    for slot in sorted(characters.keys(), key=str):
        character = characters.get(slot)
        if not isinstance(character, Mapping):
            continue
        name = _character_name(str(slot), character)
        class_current = character.get("class_current") if isinstance(character.get("class_current"), Mapping) else {}
        bio = character.get("bio") if isinstance(character.get("bio"), Mapping) else {}
        inventory = character.get("inventory") if isinstance(character.get("inventory"), Mapping) else {}
        item_names = []
        for entry in inventory.get("items") or []:
            item_id = _text(entry.get("item_id")) if isinstance(entry, Mapping) else _text(entry)
            item = items.get(item_id) if isinstance(items, Mapping) else {}
            item_names.append(_text(item.get("name")) if isinstance(item, Mapping) else item_id)
        text = _join([
            f"Name: {name}",
            f"Slot: {slot}",
            f"Klasse: {_text(class_current.get('name')) or _text(class_current.get('id'))}",
            f"Rang: {_text(class_current.get('rank'))}",
            f"Szene: {_text(character.get('scene_id'))}",
            f"Bio: {_text(bio.get('summary')) or _text(bio.get('background'))}",
            f"Items: {', '.join(name for name in item_names if name)}",
        ], "\n")
        doc = _doc(campaign_id, "character", slot, name, text, f"state.characters.{slot}", salience=0.8,
                   metadata={"entities": [name, str(slot)]})
        if doc:
            docs.append(doc)
    return docs


def _scene_docs(campaign_id: str, state: Mapping[str, Any], actor: str) -> list[RAGDocument]:
    character = ((state.get("characters") or {}).get(actor) or {}) if isinstance(state.get("characters"), Mapping) else {}
    scene_id = _text(character.get("scene_id")) if isinstance(character, Mapping) else ""
    scenes = state.get("scenes") if isinstance(state.get("scenes"), Mapping) else {}
    map_nodes = ((state.get("map") or {}).get("nodes") or {}) if isinstance(state.get("map"), Mapping) else {}
    scene = scenes.get(scene_id) if isinstance(scenes.get(scene_id), Mapping) else map_nodes.get(scene_id)
    if not isinstance(scene, Mapping):
        return []
    title = _text(scene.get("name")) or scene_id
    text = _join([f"Ort: {title}", f"Gefahr: {_text(scene.get('danger'))}", f"Notizen: {_text(scene.get('notes')) or _text(scene.get('description'))}"], "\n")
    doc = _doc(campaign_id, "current_scene", scene_id, title, text, f"state.scenes.{scene_id}", salience=0.9,
               metadata={"entities": [title, scene_id]})
    return [doc] if doc else []


def _recent_turn_docs(campaign_id: str, campaign: Mapping[str, Any]) -> list[RAGDocument]:
    turns = campaign.get("turns") if isinstance(campaign.get("turns"), list) else []
    active = [turn for turn in turns if isinstance(turn, Mapping) and turn.get("status", "active") == "active"]
    docs: list[RAGDocument] = []
    for index, turn in enumerate(active[-_MAX_RECENT_TURNS:], start=max(1, len(active) - _MAX_RECENT_TURNS + 1)):
        turn_no = turn.get("turn_number", index)
        title = f"Turn {turn_no}"
        text = _join([
            f"Actor: {_text(turn.get('actor'))}",
            f"Aktion: {_text(turn.get('input_text_display'))}",
            f"GM: {_text(turn.get('gm_text_display'))}",
        ], "\n")
        doc = _doc(campaign_id, "recent_turn", turn.get("turn_id") or turn_no, title, text,
                   f"turns[{index - 1}]", salience=0.45 + min(index, _MAX_RECENT_TURNS) * 0.03,
                   metadata={"turn_index": int(turn_no or index)})
        if doc:
            docs.append(doc)
    return docs


def _entity_docs(campaign_id: str, state: Mapping[str, Any]) -> list[RAGDocument]:
    specs = [
        ("npc", "npc_codex", "npc_id", ("name", "role_hint", "goal", "faction", "backstory_short", "status"), 0.65),
        ("item", "items", "item_id", ("name", "description", "rarity", "slot", "tags"), 0.55),
    ]
    docs: list[RAGDocument] = []
    for source_type, key, id_field, fields, salience in specs:
        records = state.get(key) if isinstance(state.get(key), Mapping) else {}
        for ident in sorted(records.keys(), key=str):
            record = records.get(ident)
            if not isinstance(record, Mapping):
                continue
            title = _text(record.get("name")) or str(ident)
            text = "\n".join(f"{field}: {record.get(field)}" for field in fields if record.get(field))
            doc = _doc(campaign_id, source_type, ident, title, text, f"state.{key}.{ident}",
                       salience=salience, metadata={id_field: str(ident), "entities": [title, str(ident)]})
            if doc:
                docs.append(doc)
    return docs


def _list_docs(campaign_id: str, state: Mapping[str, Any]) -> list[RAGDocument]:
    docs: list[RAGDocument] = []
    for idx, raw in enumerate(state.get("plotpoints") or []):
        if isinstance(raw, Mapping):
            title = _text(raw.get("title")) or _text(raw.get("id")) or f"Plotpoint {idx + 1}"
            text = _join([title, raw.get("status"), raw.get("owner"), raw.get("notes"), ", ".join(raw.get("requirements") or [])], "\n")
            doc = _doc(campaign_id, "plotpoint", raw.get("id") or idx, title, text, f"state.plotpoints[{idx}]", salience=0.7)
            if doc:
                docs.append(doc)
    for slot, character in ((state.get("characters") or {}).items() if isinstance(state.get("characters"), Mapping) else []):
        if not isinstance(character, Mapping):
            continue
        name = _character_name(str(slot), character)
        for idx, value in enumerate(character.get("conditions") or []):
            doc = _doc(campaign_id, "condition", f"{slot}:condition:{idx}", f"{name} condition", value,
                       f"state.characters.{slot}.conditions[{idx}]", salience=0.65, metadata={"entities": [name]})
            if doc:
                docs.append(doc)
        for idx, injury in enumerate(character.get("injuries") or []):
            if isinstance(injury, Mapping):
                text = _join([injury.get("title"), injury.get("severity"), injury.get("description"), injury.get("healing_stage")], "\n")
            else:
                text = _text(injury)
            doc = _doc(campaign_id, "condition", f"{slot}:injury:{idx}", f"{name} injury", text,
                       f"state.characters.{slot}.injuries[{idx}]", salience=0.7, metadata={"entities": [name]})
            if doc:
                docs.append(doc)
    return docs


def _setup_docs(campaign_id: str, campaign: Mapping[str, Any]) -> list[RAGDocument]:
    docs: list[RAGDocument] = []
    setup = campaign.get("setup") if isinstance(campaign.get("setup"), Mapping) else {}
    for section_key in ("world", "characters"):
        section = setup.get(section_key)
        if not isinstance(section, Mapping):
            continue
        sources = section.items() if section_key == "characters" else ((section_key, section),)
        for ident, payload in sources:
            if not isinstance(payload, Mapping):
                continue
            text = _join([payload.get("summary"), payload.get("answers"), payload.get("completed")], "\n")
            doc = _doc(campaign_id, "setup_answer", ident, f"Setup {ident}", text,
                       f"campaign.setup.{section_key}.{ident}", salience=0.6)
            if doc:
                docs.append(doc)
    return docs


def _world_docs(campaign_id: str, state: Mapping[str, Any]) -> list[RAGDocument]:
    docs: list[RAGDocument] = []
    world = state.get("world") if isinstance(state.get("world"), Mapping) else {}
    for key in ("settings", "bible", "elements"):
        value = world.get(key)
        if value:
            doc = _doc(campaign_id, "world_rule", key, f"World {key}", value, f"state.world.{key}", salience=0.55)
            if doc:
                docs.append(doc)
    codex = state.get("codex") if isinstance(state.get("codex"), Mapping) else {}
    for key, value in sorted(codex.items(), key=lambda row: str(row[0])):
        doc = _doc(campaign_id, "codex", key, f"Codex {key}", value, f"state.codex.{key}", salience=0.55)
        if doc:
            docs.append(doc)
    return docs


def collect_turn_rag_context(
    *,
    campaign: Mapping[str, Any],
    state: Mapping[str, Any],
    actor: str,
    action_type: str,
    content: str,
    max_results: int = 8,
) -> dict[str, Any]:
    """Collect deterministic, read-only RAG chunks for a narrator turn."""
    if not isinstance(campaign, Mapping) or not isinstance(state, Mapping):
        return {"chunks": [], "warnings": ["empty_or_malformed_state"]}
    cid = _campaign_id(campaign)
    docs: list[RAGDocument] = []
    docs.extend(_recent_turn_docs(cid, campaign))
    docs.extend(_scene_docs(cid, state, actor))
    docs.extend(_character_docs(cid, state))
    docs.extend(_entity_docs(cid, state))
    docs.extend(_list_docs(cid, state))
    docs.extend(_setup_docs(cid, campaign))
    docs.extend(_world_docs(cid, state))
    chunks = [chunk for doc in docs for chunk in chunk_document(doc, max_chars=850, overlap_chars=80)]
    query_text = _join([content, action_type, actor], " ")
    results = retrieve_chunks(RetrievalQuery(text=query_text, campaign_id=cid, entities=(actor,), max_results=max_results), chunks)
    return {
        "chunks": [
            {
                "id": result.chunk.id,
                "type": result.chunk.source_type,
                "title": _text((result.chunk.metadata or {}).get("title")) or result.chunk.document_id,
                "text": result.chunk.text,
                "score": result.score,
                "source_hint": _text((result.chunk.metadata or {}).get(_SOURCE_HINT_KEY)),
                "turn_index": (result.chunk.metadata or {}).get("turn_index"),
            }
            for result in results
        ],
        "document_count": len(docs),
        "chunk_count": len(chunks),
        "warnings": [],
    }


__all__ = ["collect_turn_rag_context"]

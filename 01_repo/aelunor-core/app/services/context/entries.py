from typing import Any, Dict, List

from app.config.codex import CODEX_KIND_BEAST, CODEX_KIND_RACE
from app.services.items.inventory import ensure_item_shape
from app.services.canon.extractor import sorted_world_profiles
from app.services.world.codex import normalize_codex_entry_stable
from app.services.world.scene import canonical_scene_id


def append_context_entry(entries: List[Dict[str, Any]], entry: Dict[str, Any]) -> None:
    title = str(entry.get("title") or "").strip()
    if not title:
        return
    entries.append(
        {
            "type": str(entry.get("type") or "unknown").strip() or "unknown",
            "id": str(entry.get("id") or "").strip(),
            "title": title,
            "aliases": list(dict.fromkeys([str(alias).strip() for alias in (entry.get("aliases") or []) if str(alias or "").strip()] + [title])),
            "facts": [str(fact).strip() for fact in (entry.get("facts") or []) if str(fact).strip()][:12],
            "sources": [
                {
                    "type": str(row.get("type") or "").strip(),
                    "id": str(row.get("id") or "").strip(),
                    "label": str(row.get("label") or "").strip(),
                }
                for row in (entry.get("sources") or [])
                if isinstance(row, dict)
            ][:8],
        }
    )


def scene_name_from_context_state(state: Dict[str, Any], scene_id: str) -> str:
    scene = ((state.get("scenes") or {}).get(scene_id) or {})
    if isinstance(scene, dict):
        return str(scene.get("name") or scene_id or "").strip()
    node = (((state.get("map") or {}).get("nodes") or {}).get(scene_id) or {})
    if isinstance(node, dict):
        return str(node.get("name") or scene_id or "").strip()
    return str(scene_id or "").strip()


def add_codex_context_entries(entries: List[Dict[str, Any]], state: Dict[str, Any]) -> None:
    race_codex = ((state.get("codex") or {}).get("races") or {}) if isinstance(((state.get("codex") or {}).get("races") or {}), dict) else {}
    for race_id, race_profile in sorted_world_profiles(state, kind=CODEX_KIND_RACE):
        codex_entry = normalize_codex_entry_stable(race_codex.get(race_id), kind=CODEX_KIND_RACE)
        known_facts = codex_entry.get("known_facts") or []
        append_context_entry(
            entries,
            {
                "type": "race",
                "id": race_id,
                "title": str((race_profile or {}).get("name") or race_id),
                "aliases": [race_id] + list((race_profile or {}).get("aliases") or []),
                "facts": known_facts if known_facts else [f"Wissensstand: {int(codex_entry.get('knowledge_level', 0) or 0)}/4"],
                "sources": [{"type": "race", "id": race_id, "label": f"Rassenkodex: {str((race_profile or {}).get('name') or race_id)}"}],
            },
        )

    beast_codex = ((state.get("codex") or {}).get("beasts") or {}) if isinstance(((state.get("codex") or {}).get("beasts") or {}), dict) else {}
    for beast_id, beast_profile in sorted_world_profiles(state, kind=CODEX_KIND_BEAST):
        codex_entry = normalize_codex_entry_stable(beast_codex.get(beast_id), kind=CODEX_KIND_BEAST)
        known_facts = codex_entry.get("known_facts") or []
        append_context_entry(
            entries,
            {
                "type": "beast",
                "id": beast_id,
                "title": str((beast_profile or {}).get("name") or beast_id),
                "aliases": [beast_id] + list((beast_profile or {}).get("aliases") or []),
                "facts": known_facts if known_facts else [f"Wissensstand: {int(codex_entry.get('knowledge_level', 0) or 0)}/4"],
                "sources": [{"type": "beast", "id": beast_id, "label": f"Bestienkodex: {str((beast_profile or {}).get('name') or beast_id)}"}],
            },
        )


def add_plot_item_scene_context_entries(entries: List[Dict[str, Any]], campaign: Dict[str, Any], state: Dict[str, Any]) -> None:
    for plotpoint in (state.get("plotpoints") or []):
        if not isinstance(plotpoint, dict):
            continue
        plot_id = str(plotpoint.get("id") or "").strip()
        title = str(plotpoint.get("title") or plot_id).strip()
        if not title:
            continue
        append_context_entry(
            entries,
            {
                "type": "plotpoint",
                "id": plot_id,
                "title": title,
                "aliases": [plot_id, title, plotpoint.get("type", ""), plotpoint.get("owner", "")],
                "facts": [
                    f"Typ: {plotpoint.get('type', 'story')}",
                    f"Status: {plotpoint.get('status', 'active')}",
                    f"Owner: {plotpoint.get('owner') or 'Kein Owner'}",
                    f"Notizen: {plotpoint.get('notes', '') or 'Keine'}",
                    f"Requirements: {', '.join(plotpoint.get('requirements') or []) or 'Keine'}",
                ],
                "sources": [{"type": "plotpoint", "id": plot_id or title, "label": f"Plotpoint: {title}"}],
            },
        )

    for item_id, raw_item in ((state.get("items") or {}).items()):
        item = ensure_item_shape(item_id, raw_item if isinstance(raw_item, dict) else {})
        append_context_entry(
            entries,
            {
                "type": "item",
                "id": item_id,
                "title": item.get("name", item_id),
                "aliases": [item_id, item.get("name", ""), item.get("slot", "")],
                "facts": [
                    f"Seltenheit: {item.get('rarity', 'common')}",
                    f"Slot: {item.get('slot', '') or 'Kein Slot'}",
                    f"Beschreibung: {item.get('description', '') or 'Keine Beschreibung.'}",
                    f"Tags: {', '.join(item.get('tags') or []) or 'Keine'}",
                ],
                "sources": [{"type": "item", "id": item_id, "label": f"Item: {item.get('name', item_id)}"}],
            },
        )

    for scene_id, scene in ((state.get("scenes") or {}).items()):
        if not isinstance(scene, dict):
            continue
        scene_name = str(scene.get("name") or scene_id).strip()
        append_context_entry(entries, {"type": "scene", "id": scene_id, "title": scene_name, "aliases": [scene_id, scene_name], "facts": [f"Gefahr: {scene.get('danger', 1)}", f"Notizen: {scene.get('notes', '') or 'Keine'}"], "sources": [{"type": "scene", "id": scene_id, "label": f"Ort: {scene_name}"}]})

    for scene_id, node in (((state.get("map") or {}).get("nodes") or {}).items()):
        node_name = str((node or {}).get("name") or scene_id).strip()
        append_context_entry(entries, {"type": "scene", "id": scene_id, "title": node_name, "aliases": [scene_id, node_name], "facts": [f"Gefahr: {int((node or {}).get('danger', 1) or 1)}", f"Typ: {str((node or {}).get('type') or 'location')}", f"Entdeckt: {'Ja' if (node or {}).get('discovered', True) else 'Nein'}"], "sources": [{"type": "scene", "id": scene_id, "label": f"Karte: {node_name}"}]})

    for faction_entry in (campaign.get("boards", {}).get("world_info") or []):
        if not isinstance(faction_entry, dict):
            continue
        if str(faction_entry.get("category") or "").strip().lower() != "faction":
            continue
        faction_id = str(faction_entry.get("entry_id") or canonical_scene_id(str(faction_entry.get("title") or "faction"))).strip()
        title = str(faction_entry.get("title") or faction_id).strip()
        append_context_entry(entries, {"type": "faction", "id": faction_id, "title": title, "aliases": [title, faction_id], "facts": [f"Beschreibung: {str(faction_entry.get('content') or '').strip() or 'Keine'}"], "sources": [{"type": "faction", "id": faction_id, "label": f"World Info: {title}"}]})

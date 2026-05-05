from typing import Any, Dict


def apply_patch_map_updates(state: Dict[str, Any], patch: Dict[str, Any]) -> None:
    state.setdefault("map", {"nodes": {}, "edges": []})
    state["map"].setdefault("nodes", {})
    for node in (patch.get("map_add_nodes") or []):
        node_id = node["id"]
        state["map"]["nodes"][node_id] = {
            "name": node["name"],
            "type": node["type"],
            "danger": node["danger"],
            "discovered": node["discovered"],
        }
        state.setdefault("scenes", {})
        state["scenes"].setdefault(node_id, {"name": node["name"], "danger": node["danger"], "notes": ""})

    for edge in (patch.get("map_add_edges") or []):
        if edge not in state["map"]["edges"]:
            state["map"]["edges"].append(edge)

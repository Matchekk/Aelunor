import hashlib
import json
import random
from typing import Any, Callable, Dict, List, Optional


def next_element_path_name(element_name: str, rank: str, path_seed: int) -> str:
    suffixes = {
        "F": ["Novize", "Student", "Lehrling"],
        "C": ["Magier", "Wandler", "Hüter"],
        "B": ["Adept", "Weber", "Kernträger"],
        "A": ["Erzrufer", "Meister", "Archon"],
        "S": ["Legende", "Erbe", "Ultimus"],
    }
    picks = suffixes.get(rank, ["Adept"])
    return f"{element_name}-{picks[path_seed % len(picks)]}"


def generate_element_class_paths(
    elements: Dict[str, Dict[str, Any]],
    summary: Dict[str, Any],
    *,
    clamp: Callable[[int, int, int], int],
    element_class_path_min: int,
    element_class_path_max: int,
    element_class_path_ranks: List[str],
    normalize_codex_alias_text: Callable[[Any], str],
    skill_rank_sort_value: Callable[[str], int],
    next_element_path_name: Callable[[str, str, int], str],
    stable_sorted_mapping: Callable[..., Dict[str, List[Dict[str, Any]]]],
) -> Dict[str, List[Dict[str, Any]]]:
    seed_text = json.dumps(
        {"theme": summary.get("theme", ""), "tone": summary.get("tone", ""), "premise": summary.get("premise", "")},
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    out: Dict[str, List[Dict[str, Any]]] = {}
    for element_id, profile in (elements or {}).items():
        if not isinstance(profile, dict):
            continue
        name = str(profile.get("name") or element_id).strip()
        path_count = clamp(1 + rng.randint(0, 2), element_class_path_min, element_class_path_max)
        paths: List[Dict[str, Any]] = []
        for path_index in range(path_count):
            path_id = f"path_{element_id}_{path_index+1}"
            rank_nodes: Dict[str, Dict[str, Any]] = {}
            for rank in element_class_path_ranks:
                rank_skill_base = normalize_codex_alias_text(name).replace(" ", "_") or "element"
                rank_nodes[rank] = {
                    "id": f"{path_id}_{rank.lower()}",
                    "name": next_element_path_name(name, rank, path_index + skill_rank_sort_value(rank)),
                    "rank": rank,
                    "element_id": element_id,
                    "description": f"Pfadstufe {rank} des Elements {name}.",
                    "required_level": 1 + (skill_rank_sort_value(rank) * 3),
                    "required_class_level": 1 + skill_rank_sort_value(rank),
                    "required_affinity_tags": list(dict.fromkeys([normalize_codex_alias_text(name), *profile.get("class_affinities", [])]))[:4],
                    "required_skills": [],
                    "core_skills_required": [
                        f"{name} {['Impuls','Schnitt','Bindung'][path_index % 3]}",
                        f"{name} Fokus",
                    ],
                    "core_skills_unlockable": [
                        f"{name} Schub {rank}",
                        f"{name} Mantel {rank}",
                    ],
                    "signature_skills": [f"{name} Signatur {rank}"],
                    "signature_theme": str(profile.get("theme") or name),
                    "next_paths": [],
                    "skill_prefix": rank_skill_base,
                }
            paths.append(
                {
                    "id": path_id,
                    "name": f"{name}-Pfad {path_index+1}",
                    "element_id": element_id,
                    "signature_theme": str(profile.get("theme") or name),
                    "ranks": rank_nodes,
                }
            )
        out[element_id] = paths
    return stable_sorted_mapping(out, key_fn=lambda item: item[0])


def normalize_class_path_rank_node(
    raw_node: Any,
    *,
    default_rank: str,
    element_id: str,
    path_id: str,
    normalize_skill_rank: Callable[[Any], str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_node, dict):
        return None
    rank = normalize_skill_rank(raw_node.get("rank", default_rank))
    node_id = str(raw_node.get("id") or f"{path_id}_{rank.lower()}").strip() or f"{path_id}_{rank.lower()}"
    name = str(raw_node.get("name") or "").strip()
    if not name:
        return None
    required_affinity_tags = [str(tag).strip() for tag in (raw_node.get("required_affinity_tags") or []) if str(tag).strip()]
    required_skills = [str(skill).strip() for skill in (raw_node.get("required_skills") or []) if str(skill).strip()]
    core_required = [str(skill).strip() for skill in (raw_node.get("core_skills_required") or []) if str(skill).strip()]
    core_unlockable = [str(skill).strip() for skill in (raw_node.get("core_skills_unlockable") or []) if str(skill).strip()]
    signature_skills = [str(skill).strip() for skill in (raw_node.get("signature_skills") or []) if str(skill).strip()]
    if not core_required:
        return None
    return {
        "id": node_id,
        "name": name,
        "rank": rank,
        "element_id": str(raw_node.get("element_id") or element_id).strip() or element_id,
        "description": str(raw_node.get("description") or "").strip(),
        "required_level": max(1, int(raw_node.get("required_level", 1) or 1)),
        "required_class_level": max(1, int(raw_node.get("required_class_level", 1) or 1)),
        "required_affinity_tags": list(dict.fromkeys(required_affinity_tags)),
        "required_skills": list(dict.fromkeys(required_skills)),
        "core_skills_required": list(dict.fromkeys(core_required)),
        "core_skills_unlockable": list(dict.fromkeys(core_unlockable)),
        "signature_skills": list(dict.fromkeys(signature_skills)),
        "signature_theme": str(raw_node.get("signature_theme") or "").strip(),
        "next_paths": [str(path).strip() for path in (raw_node.get("next_paths") or []) if str(path).strip()],
        "skill_prefix": str(raw_node.get("skill_prefix") or "").strip(),
    }

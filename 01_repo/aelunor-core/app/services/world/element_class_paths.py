import hashlib
import json
import random
from typing import Any, Callable, Dict, List


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

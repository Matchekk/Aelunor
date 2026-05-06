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


def normalize_element_class_paths(
    raw_paths: Any,
    elements: Dict[str, Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
    *,
    generate_element_class_paths: Callable[[Dict[str, Dict[str, Any]], Dict[str, Any]], Dict[str, List[Dict[str, Any]]]],
    element_class_path_max: int,
    element_class_path_ranks: List[str],
    normalize_skill_rank: Callable[[Any], str],
    deep_copy: Callable[[Any], Any],
    stable_sorted_mapping: Callable[..., Dict[str, List[Dict[str, Any]]]],
) -> Dict[str, List[Dict[str, Any]]]:
    generated_defaults = generate_element_class_paths(elements, summary or {})
    if not isinstance(raw_paths, dict):
        return generated_defaults
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    for element_id, element_profile in (elements or {}).items():
        bucket = raw_paths.get(element_id) if isinstance(raw_paths.get(element_id), list) else []
        valid_paths: List[Dict[str, Any]] = []
        for raw_path in bucket[:element_class_path_max]:
            if not isinstance(raw_path, dict):
                continue
            path_id = str(raw_path.get("id") or "").strip() or f"path_{element_id}_{len(valid_paths)+1}"
            path_name = str(raw_path.get("name") or "").strip()
            ranks_raw = raw_path.get("ranks") if isinstance(raw_path.get("ranks"), dict) else {}
            normalized_ranks: Dict[str, Dict[str, Any]] = {}
            complete = True
            for rank in element_class_path_ranks:
                node = normalize_class_path_rank_node(
                    ranks_raw.get(rank),
                    default_rank=rank,
                    element_id=element_id,
                    path_id=path_id,
                    normalize_skill_rank=normalize_skill_rank,
                )
                if not node:
                    complete = False
                    break
                normalized_ranks[rank] = node
            if not complete or not path_name:
                continue
            valid_paths.append(
                {
                    "id": path_id,
                    "name": path_name,
                    "element_id": element_id,
                    "signature_theme": str(raw_path.get("signature_theme") or element_profile.get("theme") or "").strip(),
                    "ranks": normalized_ranks,
                }
            )
        if not valid_paths:
            valid_paths = deep_copy(generated_defaults.get(element_id) or [])
        normalized[element_id] = valid_paths[:element_class_path_max]
    return stable_sorted_mapping(normalized, key_fn=lambda item: str(item[0]))


def resolve_class_path_rank_node(
    world: Dict[str, Any],
    current_class: Optional[Dict[str, Any]],
    *,
    normalize_class_current: Callable[[Optional[Dict[str, Any]]], Optional[Dict[str, Any]]],
    resolve_class_element_id: Callable[[Optional[Dict[str, Any]], Dict[str, Any]], Optional[str]],
    normalize_skill_rank: Callable[[Any], str],
    deep_copy: Callable[[Any], Any],
) -> Optional[Dict[str, Any]]:
    klass = normalize_class_current(current_class)
    if not klass:
        return None
    element_id = resolve_class_element_id(klass, world)
    if not element_id:
        return None
    all_paths = ((world.get("element_class_paths") or {}).get(element_id) or [])
    if not isinstance(all_paths, list) or not all_paths:
        return None
    wanted_path_id = str(klass.get("path_id") or "").strip()
    rank = normalize_skill_rank(klass.get("rank", "F"))
    selected_path = None
    if wanted_path_id:
        selected_path = next((path for path in all_paths if str((path or {}).get("id") or "") == wanted_path_id), None)
    if not selected_path:
        selected_path = all_paths[0]
    ranks = (selected_path or {}).get("ranks") if isinstance((selected_path or {}).get("ranks"), dict) else {}
    node = ranks.get(rank) if isinstance(ranks.get(rank), dict) else None
    if not node:
        return None
    return {
        "path_id": str((selected_path or {}).get("id") or ""),
        "path_name": str((selected_path or {}).get("name") or ""),
        "element_id": element_id,
        "rank": rank,
        "node": deep_copy(node),
    }

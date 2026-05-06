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

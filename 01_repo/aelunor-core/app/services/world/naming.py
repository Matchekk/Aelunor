from __future__ import annotations

import re


def strip_name_parenthetical(name: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\)", " ", str(name or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:!?")
    return cleaned

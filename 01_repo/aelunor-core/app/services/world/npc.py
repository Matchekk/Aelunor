from __future__ import annotations

import re
from typing import Any, Dict

from app.services.world.text_normalization import normalized_eval_text

_CONFIGURED = False


def configure(main_globals: Dict[str, Any]) -> None:
    global _CONFIGURED
    globals().update(main_globals)
    _CONFIGURED = True


def npc_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(name)).strip("_")
    if not slug:
        slug = make_id("npc").split("_", 1)[1]
    return f"npc_{slug[:48]}"


def normalize_npc_alias(text: str) -> str:
    alias = normalized_eval_text(text)
    alias = re.sub(r"\b(der|die|das|ein|eine|einen|einem|einer|herr|frau|sir|lady)\b", " ", alias)
    alias = re.sub(r"\s+", " ", alias).strip()
    return alias

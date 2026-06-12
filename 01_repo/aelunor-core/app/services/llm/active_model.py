"""Runtime-Auswahl und Persistenz des aktiven GM-Modells."""
from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import Any, Dict, Optional

from app.core.paths import DATA_DIR

LLM_SETTINGS_FILENAME = "llm_settings.json"


def _settings_path() -> str:
    return os.path.join(DATA_DIR, LLM_SETTINGS_FILENAME)


def load_persisted_model() -> Optional[str]:
    try:
        with open(_settings_path(), "r", encoding="utf-8") as handle:
            payload = json.load(handle) or {}
    except (OSError, ValueError):
        return None
    model = str(payload.get("model") or "").strip()
    return model or None


def persist_model(model: str) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = _settings_path() + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump({"model": model}, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, _settings_path())


def get_active_model() -> Dict[str, Any]:
    from app.adapters.ollama_config import OLLAMA_ADAPTER

    return {"ok": True, "model": OLLAMA_ADAPTER.settings.model}


def set_active_model(model: str) -> Dict[str, Any]:
    from app.adapters.ollama_config import OLLAMA_ADAPTER

    selected = (model or "").strip()
    if not selected:
        return {
            "ok": False,
            "model": OLLAMA_ADAPTER.settings.model,
            "message": "Kein GM-Modell gewählt.",
        }
    OLLAMA_ADAPTER.settings = replace(OLLAMA_ADAPTER.settings, model=selected)
    persist_model(selected)
    return {"ok": True, "model": selected, "message": f"GM-Modell aktiv: {selected}"}

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def normalize_ollama_base_url(value: Optional[str]) -> str:
    raw_value = (value or "").strip()
    raw = (raw_value or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Ollama Base URL muss eine http(s)-URL sein.")
    if parsed.hostname not in _LOCAL_HOSTS:
        raise ValueError("In Phase 1 sind nur lokale Ollama-URLs erlaubt.")
    return raw


def _model_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    details = entry.get("details") if isinstance(entry.get("details"), dict) else {}
    return {
        "name": str(entry.get("name") or "").strip(),
        "modifiedAt": entry.get("modified_at"),
        "size": entry.get("size"),
        "family": details.get("family"),
        "details": details or None,
    }


def list_ollama_models(*, base_url: Optional[str], timeout: float = 2.5) -> Dict[str, Any]:
    try:
        normalized_url = normalize_ollama_base_url(base_url)
        response = requests.get(f"{normalized_url}/api/tags", timeout=timeout)
        response.raise_for_status()
        payload = response.json() or {}
        models = [
            model
            for model in (_model_entry(entry) for entry in payload.get("models", []) or [])
            if model["name"]
        ]
        return {
            "ok": True,
            "status": "connected",
            "message": f"{len(models)} lokale Ollama-Modelle gefunden.",
            "models": models,
        }
    except ValueError as exc:
        return {"ok": False, "status": "error", "message": str(exc), "models": []}
    except requests.RequestException as exc:
        return {
            "ok": False,
            "status": "offline",
            "message": f"Ollama ist nicht erreichbar: {exc.__class__.__name__}",
            "models": [],
        }
    except Exception as exc:
        return {"ok": False, "status": "error", "message": f"Ollama-Scan fehlgeschlagen: {exc.__class__.__name__}", "models": []}


def test_ollama_model(*, base_url: Optional[str], model: Optional[str], timeout: float = 8.0) -> Dict[str, Any]:
    selected_model = (model or "").strip()
    if not selected_model:
        return {"ok": False, "message": "Kein GM-Modell gewählt.", "latencyMs": None}
    try:
        normalized_url = normalize_ollama_base_url(base_url)
    except ValueError as exc:
        return {"ok": False, "message": str(exc), "latencyMs": None}

    started = time.perf_counter()
    try:
        response = requests.post(
            f"{normalized_url}/api/chat",
            json={
                "model": selected_model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "Antworte extrem kurz."},
                    {"role": "user", "content": "Sag nur: bereit"},
                ],
                "options": {"temperature": 0.0, "num_ctx": 512},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {"ok": True, "message": "GM-Modell antwortet.", "latencyMs": latency_ms}
    except requests.RequestException as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {"ok": False, "message": f"GM-Test fehlgeschlagen: {exc.__class__.__name__}", "latencyMs": latency_ms}

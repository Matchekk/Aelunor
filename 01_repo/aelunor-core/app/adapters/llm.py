import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from app.core.turn_profiling import record_llm_call


@dataclass(frozen=True)
class OllamaSettings:
    url: str
    model: str
    timeout_sec: int
    seed: Optional[int]
    temperature: float
    num_ctx: int
    repeat_penalty: float
    repeat_last_n: int


class OllamaAdapter:
    def __init__(self, settings: OllamaSettings) -> None:
        self.settings = settings

    def request_seed(self) -> Optional[int]:
        if self.settings.seed is not None:
            return int(self.settings.seed)
        return int.from_bytes(secrets.token_bytes(4), "big")

    def tags(self, *, timeout: int = 15) -> Dict[str, Any]:
        response = requests.get(f"{self.settings.url}/api/tags", timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:300]}")
        return response.json() or {}

    def status_payload(self) -> Dict[str, Any]:
        available_models: List[Dict[str, Any]] = []
        ollama_ok = False
        error = ""
        try:
            payload = self.tags(timeout=15)
            available_models = payload.get("models", []) or []
            ollama_ok = True
        except Exception as exc:
            error = str(exc)
        return {
            "ollama_url": self.settings.url,
            "configured_model": self.settings.model,
            "request_timeout_sec": self.settings.timeout_sec,
            "seed": self.settings.seed,
            "temperature": self.settings.temperature,
            "num_ctx": self.settings.num_ctx,
            "ollama_ok": ollama_ok,
            "configured_model_available": any((entry or {}).get("name") == self.settings.model for entry in available_models),
            "available_models": [
                {
                    "name": entry.get("name"),
                    "size": entry.get("size"),
                    "parameter_size": ((entry.get("details") or {}).get("parameter_size")),
                    "family": ((entry.get("details") or {}).get("family")),
                }
                for entry in available_models
            ],
            "error": error,
        }

    def chat(
        self,
        system: str,
        user: str,
        *,
        format_schema: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        temperature: Optional[float] = None,
        repeat_penalty: Optional[float] = None,
        num_ctx: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
        request_timeout = max(30, int(timeout or self.settings.timeout_sec))
        options: Dict[str, Any] = {
            "temperature": self.settings.temperature if temperature is None else temperature,
            "num_ctx": self.settings.num_ctx if num_ctx is None else num_ctx,
            "repeat_penalty": self.settings.repeat_penalty if repeat_penalty is None else repeat_penalty,
            "repeat_last_n": self.settings.repeat_last_n,
        }
        seed = self.request_seed()
        if seed is not None:
            options["seed"] = seed
        request_model = (model or "").strip() or self.settings.model
        payload: Dict[str, Any] = {
            "model": request_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": options,
        }
        if format_schema is not None:
            payload["format"] = format_schema
        started = time.perf_counter()
        response = requests.post(f"{self.settings.url}/api/chat", json=payload, timeout=request_timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:500]}")
        body = response.json()
        content = (body.get("message", {}) or {}).get("content", "").strip()
        record_llm_call(
            duration_s=time.perf_counter() - started,
            model=request_model,
            num_ctx=int(options["num_ctx"]),
            temperature=float(options["temperature"]),
            prompt_chars=len(system) + len(user),
            response_chars=len(content),
            has_schema=format_schema is not None,
            prompt_tokens=int(body.get("prompt_eval_count") or 0),
            response_tokens=int(body.get("eval_count") or 0),
        )
        return content

"""Experimenteller LLM-Adapter für einen OpenAI-kompatiblen llama.cpp-Server.

Spiegelt das duck-typed Interface des OllamaAdapter (``chat`` / ``request_seed`` /
``status_payload``), damit er drop-in via ``LLM_PROVIDER=llama_cpp_openai`` genutzt
werden kann. Default bleibt Ollama.

Server-Start (siehe docs/performance/llama_cpp_setup.md):
  llama-server.exe -m <gguf> --port 8088 --host 127.0.0.1 -c 32768 -ngl 99 -fa on

Vorteil-Hypothese: grammar-constrained JSON (``response_format: json_schema``) liefert
garantiert valides JSON → eliminiert Ollamas Schema-Retry-Varianz. Roh-Speed nur ~5-10 %
besser, daher experimentell/PARK (Ollama bleibt Default).
"""
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from app.core.turn_profiling import record_llm_call


@dataclass(frozen=True)
class LlamaCppSettings:
    base_url: str  # inkl. /v1, z.B. http://127.0.0.1:8088/v1
    model: str     # llama-server ignoriert das Feld inhaltlich, OpenAI-Clients brauchen es
    timeout_sec: int
    temperature: float
    num_ctx: int
    max_tokens: int
    seed: Optional[int]
    # Anti-Repetition: llama.cpp default repeat_penalty ist 1.0 (keine Strafe).
    # Ohne diese Werte laufen Retry-/Repair-Calls in Wiederholungs-Runaways.
    repeat_penalty: float = 1.18
    repeat_last_n: int = 192


class LlamaCppOpenAIAdapter:
    def __init__(self, settings: LlamaCppSettings) -> None:
        self.settings = settings

    def request_seed(self) -> Optional[int]:
        if self.settings.seed is not None:
            return int(self.settings.seed)
        return int.from_bytes(secrets.token_bytes(4), "big")

    def status_payload(self) -> Dict[str, Any]:
        ok = False
        error = ""
        models = []
        try:
            r = requests.get(f"{self.settings.base_url}/models", timeout=10)
            ok = r.status_code == 200
            if ok:
                models = [m.get("id") for m in (r.json() or {}).get("data", [])]
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return {
            "provider": "llama_cpp_openai",
            "base_url": self.settings.base_url,
            "configured_model": self.settings.model,
            "request_timeout_sec": self.settings.timeout_sec,
            "llama_cpp_ok": ok,
            "available_models": models,
            "error": error,
        }

    def _unreachable_message(self, exc: Exception) -> str:
        return (
            "llama.cpp provider selected but LLAMA_CPP_BASE_URL is not reachable: "
            f"{self.settings.base_url} ({type(exc).__name__}: {exc}).\n"
            "Aelunor does NOT silently fall back to Ollama — start the llama.cpp server, e.g.:\n"
            "  llama-server.exe -m <gguf> --host 127.0.0.1 --port 8088 -c 32768 -ngl 99 -fa on\n"
            f"Config: LLAMA_CPP_BASE_URL={self.settings.base_url}  LLAMA_CPP_MODEL={self.settings.model}\n"
            "Or select the legacy provider explicitly: AELUNOR_LLM_PROVIDER=ollama"
        )

    def _post_chat(self, payload: Dict[str, Any], timeout: int) -> requests.Response:
        try:
            return requests.post(f"{self.settings.base_url}/chat/completions", json=payload, timeout=timeout)
        except requests.exceptions.RequestException as exc:
            # No silent fallback: surface an actionable error instead of a raw
            # transport stack trace (and never quietly switch to Ollama).
            raise RuntimeError(self._unreachable_message(exc)) from exc

    def chat(
        self,
        system: str,
        user: str,
        *,
        format_schema: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        temperature: Optional[float] = None,
        repeat_penalty: Optional[float] = None,  # llama.cpp-native Extension auf /v1/chat/completions
        num_ctx: Optional[int] = None,           # serverseitig per -c gesetzt -> nur Profiling
        model: Optional[str] = None,
    ) -> str:
        request_timeout = max(30, int(timeout or self.settings.timeout_sec))
        request_model = (model or "").strip() or self.settings.model
        temp = self.settings.temperature if temperature is None else temperature
        # repeat_penalty / repeat_last_n sind llama.cpp-native Sampler-Felder, die
        # der OpenAI-kompatible llama-server aus dem Request liest. Ohne sie greift
        # der Server-Default 1.0 (keine Strafe) -> Retry-/Repair-Runaways.
        effective_repeat_penalty = (
            self.settings.repeat_penalty if repeat_penalty is None else float(repeat_penalty)
        )
        base_payload: Dict[str, Any] = {
            "model": request_model,
            "stream": False,
            "temperature": temp,
            "max_tokens": self.settings.max_tokens,
            "seed": self.request_seed(),
            "repeat_penalty": effective_repeat_penalty,
            "repeat_last_n": self.settings.repeat_last_n,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        started = time.perf_counter()
        response: Optional[requests.Response] = None
        if format_schema is not None:
            # 1) grammar-constrained strict JSON-Schema (garantiert valide)
            payload = dict(base_payload)
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "aelunor_turn", "strict": True, "schema": format_schema},
            }
            response = self._post_chat(payload, request_timeout)
            if response.status_code != 200:
                # 2) Fallback: json_object + Schema im Prompt (falls strict-Grammar abgelehnt)
                fb_user = (
                    user
                    + "\n\nAntworte ausschließlich mit einem einzelnen gültigen JSON-Objekt gemäß diesem "
                    + "Schema. Keine Markdown-Fences, keine Erklärung.\n\nSCHEMA:\n"
                    + json.dumps(format_schema, ensure_ascii=False)
                )
                payload = dict(base_payload)
                payload["messages"] = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": fb_user},
                ]
                payload["response_format"] = {"type": "json_object"}
                response = self._post_chat(payload, request_timeout)
        else:
            response = self._post_chat(base_payload, request_timeout)

        if response.status_code != 200:
            raise RuntimeError(f"llama.cpp error {response.status_code}: {response.text[:500]}")
        body = response.json()
        choice0 = (body.get("choices") or [{}])[0]
        content = ((choice0.get("message") or {}).get("content", "") or "")
        content = content.strip()
        usage = body.get("usage") or {}
        _diag_path = os.getenv("AELUNOR_LLM_DIAG", "").strip()
        if _diag_path:
            try:
                json.loads(content)
                _json_ok = True
            except Exception:
                _json_ok = False
            try:
                import hashlib
                with open(_diag_path, "a", encoding="utf-8") as _f:
                    _f.write(json.dumps({
                        "finish_reason": choice0.get("finish_reason"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "content_len": len(content),
                        "has_schema": format_schema is not None,
                        "json_parse_ok": _json_ok,
                        "content_sha8": hashlib.sha1(content.encode("utf-8", "replace")).hexdigest()[:8],
                        "head": content[:160],
                        "tail": content[-160:],
                    }, ensure_ascii=False) + "\n")
            except OSError:
                pass
        record_llm_call(
            duration_s=time.perf_counter() - started,
            model=request_model,
            num_ctx=self.settings.num_ctx if num_ctx is None else int(num_ctx),
            temperature=float(temp),
            prompt_chars=len(system) + len(user),
            response_chars=len(content),
            has_schema=format_schema is not None,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            response_tokens=int(usage.get("completion_tokens") or 0),
        )
        return content

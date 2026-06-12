"""Optionales Turn-Profiling (AELUNOR_PROFILE_TURNS=1).

Misst Phasen der Turn-Pipeline und alle LLM-Calls (Dauer, Modell, num_ctx,
Groessen) und schreibt pro Turn genau eine maschinenlesbare JSON-Zeile.
Prompt-Inhalte werden nie geloggt, nur Laengen.
"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger("aelunor.turn_profile")


def profiling_enabled() -> bool:
    return str(os.getenv("AELUNOR_PROFILE_TURNS", "")).strip().lower() in {"1", "true", "yes"}


class TurnProfiler:
    def __init__(self, *, actor: str, action_type: str) -> None:
        self.started = time.perf_counter()
        self.meta: Dict[str, Any] = {"actor": actor, "action_type": action_type}
        self.phases: List[Dict[str, Any]] = []
        self.llm_calls: List[Dict[str, Any]] = []
        self._active_phase: str = ""

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        previous = self._active_phase
        self._active_phase = name
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.phases.append({"name": name, "s": round(time.perf_counter() - t0, 2)})
            self._active_phase = previous

    def record_llm_call(
        self,
        *,
        duration_s: float,
        model: str,
        num_ctx: int,
        temperature: float,
        prompt_chars: int,
        response_chars: int,
        has_schema: bool,
        prompt_tokens: int = 0,
        response_tokens: int = 0,
    ) -> None:
        self.llm_calls.append(
            {
                "phase": self._active_phase or "unphased",
                "s": round(duration_s, 2),
                "model": model,
                "num_ctx": num_ctx,
                "temp": temperature,
                "prompt_chars": prompt_chars,
                "response_chars": response_chars,
                "prompt_tokens": prompt_tokens,
                "response_tokens": response_tokens,
                "schema": has_schema,
            }
        )

    def finish(self, **extra: Any) -> Dict[str, Any]:
        report = {
            "kind": "turn_profile",
            "total_s": round(time.perf_counter() - self.started, 2),
            "llm_total_s": round(sum(entry["s"] for entry in self.llm_calls), 2),
            "llm_calls": self.llm_calls,
            "phases": self.phases,
            **self.meta,
            **extra,
        }
        line = json.dumps(report, ensure_ascii=False)
        logger.info(line)
        path = str(os.getenv("AELUNOR_PROFILE_PATH", "")).strip()
        if path:
            try:
                with open(path, "a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            except OSError:
                pass
        return report


_CURRENT: ContextVar[Optional[TurnProfiler]] = ContextVar("aelunor_turn_profiler", default=None)


def start_turn_profile(*, actor: str, action_type: str) -> Optional[TurnProfiler]:
    if not profiling_enabled():
        return None
    profiler = TurnProfiler(actor=actor, action_type=action_type)
    _CURRENT.set(profiler)
    return profiler


def current_profiler() -> Optional[TurnProfiler]:
    return _CURRENT.get()


def end_turn_profile() -> None:
    _CURRENT.set(None)


@contextmanager
def profile_phase(name: str) -> Iterator[None]:
    profiler = _CURRENT.get()
    if profiler is None:
        yield
        return
    with profiler.phase(name):
        yield


def record_llm_call(
    *,
    duration_s: float,
    model: str,
    num_ctx: int,
    temperature: float,
    prompt_chars: int,
    response_chars: int,
    has_schema: bool,
    prompt_tokens: int = 0,
    response_tokens: int = 0,
) -> None:
    profiler = _CURRENT.get()
    if profiler is None:
        return
    profiler.record_llm_call(
        duration_s=duration_s,
        model=model,
        num_ctx=num_ctx,
        temperature=temperature,
        prompt_chars=prompt_chars,
        response_chars=response_chars,
        has_schema=has_schema,
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
    )

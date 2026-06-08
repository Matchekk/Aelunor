from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol

from app.services.llm.json_repair import (
    extract_json_payload,
    ollama_format_fallback_needed,
    schema_fallback_instruction,
)


class ChatAdapter(Protocol):
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
    ) -> str:
        ...


EmitTurnPhaseEvent = Callable[..., None]
TurnFlowErrorFactory = Callable[..., Exception]


@dataclass(frozen=True)
class LlmClientSettings:
    timeout_sec: int
    temperature: float
    response_schema: Dict[str, Any]
    error_code_json_repair: str


def _noop_emit(*_args: Any, **_kwargs: Any) -> None:
    return None


def call_ollama_text(
    adapter: ChatAdapter,
    settings: LlmClientSettings,
    system: str,
    user: str,
) -> str:
    return adapter.chat(
        system,
        user,
        timeout=max(30, settings.timeout_sec),
        temperature=0.35,
        num_ctx=4096,
    )


def call_ollama_chat(
    adapter: ChatAdapter,
    settings: LlmClientSettings,
    system: str,
    user: str,
    *,
    format_schema: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
    temperature: Optional[float] = None,
    repeat_penalty: Optional[float] = None,
) -> str:
    request_timeout = max(30, int(timeout or settings.timeout_sec))
    try:
        return adapter.chat(
            system,
            user,
            format_schema=format_schema,
            timeout=request_timeout,
            temperature=temperature,
            repeat_penalty=repeat_penalty,
        )
    except RuntimeError as exc:
        message = str(exc)
        if format_schema is not None and ollama_format_fallback_needed(message):
            fallback_user = (
                user
                + "\n\nWICHTIGER FALLBACK-HINWEIS:\n"
                + "Das Modell konnte das Schema-Format nicht verwenden. "
                + schema_fallback_instruction(format_schema)
            )
            return call_ollama_chat(
                adapter,
                settings,
                system,
                fallback_user,
                format_schema=None,
                timeout=request_timeout,
                temperature=temperature,
                repeat_penalty=repeat_penalty,
            )
        raise


def repair_json_payload_with_model(
    adapter: ChatAdapter,
    settings: LlmClientSettings,
    system: str,
    broken_content: str,
    *,
    schema: Dict[str, Any],
    timeout: int = 90,
) -> Dict[str, Any]:
    repair_user = (
        "Die folgende Modellantwort sollte JSON sein, ist aber kaputt oder unvollstÃ¤ndig.\n"
        "Repariere sie zu einem einzelnen gÃ¼ltigen JSON-Objekt gemÃ¤ÃŸ Schema.\n"
        "Regeln:\n"
        "- Keine Markdown-Fences\n"
        "- Keine ErklÃ¤rung\n"
        "- Fehlende optionale Felder mit leeren Standardwerten fÃ¼llen\n"
        "- Wenn ein Feld im Schema ein Objekt erwartet, gib kein Array zurÃ¼ck\n"
        "- Halte vorhandene Inhalte so gut wie mÃ¶glich inhaltlich stabil\n\n"
        "SCHEMA:\n"
        + json.dumps(schema, ensure_ascii=False)
        + "\n\nKAPUTTE_ANTWORT:\n"
        + str(broken_content or "")[:6000]
    )
    repaired = call_ollama_chat(
        adapter,
        settings,
        system,
        repair_user,
        format_schema=schema,
        timeout=timeout,
        temperature=0.05,
        repeat_penalty=1.05,
    )
    return extract_json_payload(repaired)


def call_ollama_json(
    adapter: ChatAdapter,
    settings: LlmClientSettings,
    system: str,
    user: str,
    *,
    temperature: Optional[float] = None,
    repeat_penalty: Optional[float] = None,
    trace_ctx: Optional[Dict[str, Any]] = None,
    emit_turn_phase_event: EmitTurnPhaseEvent = _noop_emit,
    turn_flow_error: Optional[TurnFlowErrorFactory] = None,
) -> Dict[str, Any]:
    content = call_ollama_chat(
        adapter,
        settings,
        system,
        user,
        format_schema=settings.response_schema,
        timeout=max(180, settings.timeout_sec),
        temperature=settings.temperature if temperature is None else temperature,
        repeat_penalty=repeat_penalty,
    )
    try:
        parsed = extract_json_payload(content)
        emit_turn_phase_event(
            trace_ctx,
            phase="narrator_json_parse_repair",
            success=True,
            extra={"mode": "parse_ok"},
        )
        return parsed
    except RuntimeError as exc:
        if "Model returned non-JSON content" not in str(exc) and "Model returned empty content" not in str(exc):
            raise
        emit_turn_phase_event(
            trace_ctx,
            phase="narrator_json_parse_repair",
            success=False,
            error_code=settings.error_code_json_repair,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"mode": "parse_failed_repair_attempt"},
        )
        try:
            repaired = repair_json_payload_with_model(
                adapter,
                settings,
                system,
                content,
                schema=settings.response_schema,
            )
        except Exception as repair_exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="narrator_json_parse_repair",
                success=False,
                error_code=settings.error_code_json_repair,
                error_class=repair_exc.__class__.__name__,
                message=str(repair_exc)[:240],
                extra={"mode": "repair_failed"},
            )
            if trace_ctx is not None and turn_flow_error is not None:
                raise turn_flow_error(
                    error_code=settings.error_code_json_repair,
                    phase="narrator_json_parse_repair",
                    trace_ctx=trace_ctx,
                    exc=repair_exc,
                )
            raise
        emit_turn_phase_event(
            trace_ctx,
            phase="narrator_json_parse_repair",
            success=True,
            extra={"mode": "repair_ok"},
        )
        return repaired


def call_ollama_schema(
    adapter: ChatAdapter,
    settings: LlmClientSettings,
    system: str,
    user: str,
    schema: Dict[str, Any],
    *,
    timeout: Optional[int] = None,
    temperature: float = 0.45,
) -> Dict[str, Any]:
    schema_timeout = max(90, int(timeout or settings.timeout_sec))
    content = call_ollama_chat(
        adapter,
        settings,
        system,
        user,
        format_schema=schema,
        timeout=schema_timeout,
        temperature=temperature,
    )
    try:
        return extract_json_payload(content)
    except RuntimeError as exc:
        if "Model returned non-JSON content" not in str(exc) and "Model returned empty content" not in str(exc):
            raise
        return repair_json_payload_with_model(
            adapter,
            settings,
            system,
            content,
            schema=schema,
            timeout=min(schema_timeout, 120),
        )


def build_default_llm_client_settings(
    *,
    timeout_sec: int,
    temperature: float,
    response_schema: Dict[str, Any],
    error_code_json_repair: str,
) -> LlmClientSettings:
    return LlmClientSettings(
        timeout_sec=timeout_sec,
        temperature=temperature,
        response_schema=response_schema,
        error_code_json_repair=error_code_json_repair,
    )

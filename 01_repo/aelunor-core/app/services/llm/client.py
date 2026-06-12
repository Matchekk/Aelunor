from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol

from app.services.llm.call_profiles import extractor_profile, narrator_profile, repair_profile
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
        **kwargs: Any,
    ) -> str:
        ...


EmitTurnPhaseEvent = Callable[..., None]
TurnFlowErrorFactory = Callable[..., Exception]

def repairable_content(content: Any) -> bool:
    """Nur Antworten mit Nutzinformation sind reparierbar.

    Nach Kontext-Truncation liefern lokale Modelle typischerweise leere oder
    degenerierte Antworten (nur Klammern/Backticks/Whitespace). Ein Repair-
    Lauf darauf erzeugt nur eine inhaltslose Schema-Attrappe.
    """
    return bool(re.sub(r"[\s`'\"{}\[\],:]+", "", str(content or "")))


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
    # Kein hartes num_ctx=4096 mehr: die Memory-Zusammenfassung bekommt ~30k
    # Zeichen Input; bei 4096 wurde der Prompt abgeschnitten und das Modell
    # lieferte konsequent leere Antworten. Der Adapter-Default vermeidet
    # zusaetzlich den Kontextwechsel (Model-Reload) mitten im Turn.
    return adapter.chat(
        system,
        user,
        timeout=max(30, settings.timeout_sec),
        temperature=0.35,
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
    num_ctx: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    request_timeout = max(30, int(timeout or settings.timeout_sec))
    # Nur gesetzte Overrides weiterreichen, damit Adapter ohne diese
    # Parameter (z. B. Test-Fakes) unveraendert funktionieren.
    profile_kwargs: Dict[str, Any] = {}
    if num_ctx is not None:
        profile_kwargs["num_ctx"] = num_ctx
    if model is not None:
        profile_kwargs["model"] = model
    try:
        return adapter.chat(
            system,
            user,
            format_schema=format_schema,
            timeout=request_timeout,
            temperature=temperature,
            repeat_penalty=repeat_penalty,
            **profile_kwargs,
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
                num_ctx=num_ctx,
                model=model,
            )
        raise


def repair_json_payload_with_model(
    adapter: ChatAdapter,
    settings: LlmClientSettings,
    system: str,
    broken_content: str,
    *,
    schema: Dict[str, Any],
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    # Local models routinely need far longer than a fixed 90s for the repair
    # pass; without an explicit override the configured timeout must apply.
    repair_timeout = max(90, int(timeout or settings.timeout_sec))
    profile = repair_profile()
    repair_user = (
        "Die folgende Modellantwort sollte JSON sein, ist aber kaputt oder unvollständig.\n"
        "Repariere sie zu einem einzelnen gültigen JSON-Objekt gemäß Schema.\n"
        "Regeln:\n"
        "- Keine Markdown-Fences\n"
        "- Keine Erklärung\n"
        "- Fehlende optionale Felder mit leeren Standardwerten füllen\n"
        "- Wenn ein Feld im Schema ein Objekt erwartet, gib kein Array zurück\n"
        "- Halte vorhandene Inhalte so gut wie möglich inhaltlich stabil\n\n"
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
        timeout=repair_timeout,
        temperature=0.05,
        repeat_penalty=1.05,
        num_ctx=profile.num_ctx,
        model=profile.model,
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
    profile = narrator_profile()
    content = call_ollama_chat(
        adapter,
        settings,
        system,
        user,
        format_schema=settings.response_schema,
        timeout=max(180, settings.timeout_sec),
        temperature=settings.temperature if temperature is None else temperature,
        repeat_penalty=repeat_penalty,
        num_ctx=profile.num_ctx,
        model=profile.model,
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
        retry_user = (
            user
            + "\n\nWICHTIG: Der vorherige schema-formatierte Aufruf war leer oder kein JSON. "
            + schema_fallback_instruction(settings.response_schema)
        )
        try:
            retry_content = call_ollama_chat(
                adapter,
                settings,
                system,
                retry_user,
                format_schema=None,
                timeout=max(180, settings.timeout_sec),
                temperature=max(0.35, settings.temperature - 0.1),
                repeat_penalty=repeat_penalty,
                num_ctx=profile.num_ctx,
                model=profile.model,
            )
            parsed_retry = extract_json_payload(retry_content)
            emit_turn_phase_event(
                trace_ctx,
                phase="narrator_json_parse_repair",
                success=True,
                extra={"mode": "formatless_retry_ok"},
            )
            return parsed_retry
        except Exception as retry_exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="narrator_json_parse_repair",
                success=False,
                error_code=settings.error_code_json_repair,
                error_class=retry_exc.__class__.__name__,
                message=str(retry_exc)[:240],
                extra={"mode": "formatless_retry_failed"},
            )
        try:
            if not repairable_content(content):
                # Degenerierte Narrator-Antwort: Repair haette keinerlei
                # Inhalt als Basis und wuerde eine kontextlose Story
                # halluzinieren. Stattdessen scheitern lassen, damit der
                # Turn-Retry mit vollem Kontext neu ansetzt.
                raise RuntimeError("Model returned empty content; nothing to repair")
            repaired = repair_json_payload_with_model(
                adapter,
                settings,
                system,
                content,
                schema=settings.response_schema,
                timeout=max(180, settings.timeout_sec),
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
    profile = extractor_profile()
    content = call_ollama_chat(
        adapter,
        settings,
        system,
        user,
        format_schema=schema,
        timeout=schema_timeout,
        temperature=temperature,
        num_ctx=profile.num_ctx,
        model=profile.model,
    )
    try:
        return extract_json_payload(content)
    except RuntimeError as exc:
        if "Model returned non-JSON content" not in str(exc) and "Model returned empty content" not in str(exc):
            raise
        if not repairable_content(content):
            raise
        # The repair pass must get the same budget as the schema call itself;
        # a 120s cap reliably times out on local models.
        return repair_json_payload_with_model(
            adapter,
            settings,
            system,
            content,
            schema=schema,
            timeout=schema_timeout,
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

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from app.services.llm.client import LlmClientSettings
from app.services.llm import client as llm_client


@dataclass(frozen=True)
class TurnLlmDependencies:
    call_ollama_json: Callable[..., Dict[str, Any]]
    call_ollama_schema: Callable[..., Dict[str, Any]]


@dataclass(frozen=True)
class TurnExtractionDependencies:
    build_extractor_context_packet: Callable[..., Dict[str, Any]]
    call_canon_extractor: Callable[..., Dict[str, Any]]
    call_npc_extractor: Callable[..., list[Dict[str, Any]]]
    apply_npc_upserts: Callable[..., list[Dict[str, Any]]]
    run_canon_gate: Callable[..., Dict[str, Any]]
    normalize_npc_codex_state: Callable[..., None]


@dataclass(frozen=True)
class TurnProgressionDependencies:
    append_character_change_events: Callable[..., None]
    apply_progression_events: Callable[..., Dict[str, Any]]
    apply_skill_events: Callable[..., list[Any]]


@dataclass(frozen=True)
class TurnCodexDependencies:
    collect_codex_triggers: Callable[..., Dict[str, Any]]
    apply_codex_triggers: Callable[..., list[Dict[str, Any]]]


@dataclass(frozen=True)
class TurnPacingDependencies:
    active_pacing_profile: Callable[..., Dict[str, Any]]
    milestone_state_for_turn: Callable[..., Dict[str, Any]]
    compute_turn_budget_estimates: Callable[..., None]
    build_pacing_instruction_block: Callable[..., str]
    update_turn_timing_ema: Callable[..., None]


@dataclass(frozen=True)
class TurnAttributeDependencies:
    normalize_attribute_influence_meta: Callable[..., Dict[str, Any]]


def build_turn_llm_dependencies(
    *,
    adapter: llm_client.ChatAdapter,
    settings: LlmClientSettings,
    emit_turn_phase_event: Callable[..., None],
    turn_flow_error: Callable[..., Exception],
) -> TurnLlmDependencies:
    def call_json(
        system: str,
        user: str,
        *,
        temperature: Optional[float] = None,
        repeat_penalty: Optional[float] = None,
        trace_ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return llm_client.call_ollama_json(
            adapter,
            settings,
            system,
            user,
            temperature=temperature,
            repeat_penalty=repeat_penalty,
            trace_ctx=trace_ctx,
            emit_turn_phase_event=emit_turn_phase_event,
            turn_flow_error=turn_flow_error,
        )

    def call_schema(
        system: str,
        user: str,
        schema: Dict[str, Any],
        *,
        timeout: Optional[int] = None,
        temperature: float = 0.45,
    ) -> Dict[str, Any]:
        return llm_client.call_ollama_schema(
            adapter,
            settings,
            system,
            user,
            schema,
            timeout=timeout,
            temperature=temperature,
        )

    return TurnLlmDependencies(
        call_ollama_json=call_json,
        call_ollama_schema=call_schema,
    )

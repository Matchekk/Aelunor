from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Optional, Tuple

from app.core.ids import deep_copy
from app.services.patch_payloads import merge_patch_payloads
from app.services.state_basics import blank_patch


def _missing_dependency(name: str) -> Callable[..., Any]:
    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"Canon patch gate dependency is not configured: {name}")
    return _missing


def _noop_emit_turn_phase_event(*_args: Any, **_kwargs: Any) -> None:
    return None


@dataclass(frozen=True)
class CanonPatchGateDependencies:
    apply_patch: Callable[..., Dict[str, Any]] = _missing_dependency("apply_patch")
    attribute_cap_for_campaign: Callable[..., int] = _missing_dependency("attribute_cap_for_campaign")
    emit_turn_phase_event: Callable[..., None] = _noop_emit_turn_phase_event
    sanitize_patch: Callable[..., Dict[str, Any]] = _missing_dependency("sanitize_patch")
    validate_patch: Callable[..., None] = _missing_dependency("validate_patch")


_DEPS = CanonPatchGateDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def apply_canon_gate_patch(
    campaign: Dict[str, Any],
    *,
    state_after: Dict[str, Any],
    merged_patch: Dict[str, Any],
    merged_with_gate: Dict[str, Any],
    actor: str,
    trace_ctx: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    gate_patch = blank_patch()
    gate_patch["characters"][actor] = deep_copy((merged_with_gate.get("characters") or {}).get(actor) or {})

    _DEPS.emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "canon_gate"})
    gate_patch = _DEPS.sanitize_patch(state_after, gate_patch)
    _DEPS.emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "canon_gate", "result": "ok"})
    _DEPS.emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "canon_gate"})
    _DEPS.validate_patch(state_after, gate_patch)
    _DEPS.emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "canon_gate", "result": "ok"})
    _DEPS.emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "canon_gate"})
    next_state = _DEPS.apply_patch(state_after, gate_patch, attribute_cap=_DEPS.attribute_cap_for_campaign(campaign))
    _DEPS.emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "canon_gate", "result": "ok"})
    return next_state, merge_patch_payloads(merged_patch, gate_patch)

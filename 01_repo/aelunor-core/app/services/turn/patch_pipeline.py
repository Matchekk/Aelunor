from typing import Any, Callable, Dict, Optional


def apply_patch_with_events(
    state: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    stage: str,
    trace_ctx: Optional[Dict[str, Any]],
    attribute_cap: int,
    apply_patch: Callable[..., Dict[str, Any]],
    emit_turn_phase_event: Callable[..., None],
    turn_flow_error: Callable[..., Exception],
    error_code_patch_apply: str,
    extractor_apply_stage: str = "",
) -> Dict[str, Any]:
    try:
        emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": stage})
        next_state = apply_patch(state, patch, attribute_cap=attribute_cap)
        emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": stage, "result": "ok"})
        if extractor_apply_stage:
            emit_turn_phase_event(trace_ctx, phase="extractor_patch_apply", success=True, extra={"stage": extractor_apply_stage, "result": "ok"})
        return next_state
    except Exception as exc:
        emit_turn_phase_event(
            trace_ctx,
            phase="patch_apply",
            success=False,
            error_code=error_code_patch_apply,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"stage": stage},
        )
        if extractor_apply_stage:
            emit_turn_phase_event(
                trace_ctx,
                phase="extractor_patch_apply",
                success=False,
                error_code=error_code_patch_apply,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": extractor_apply_stage},
            )
        raise turn_flow_error(
            error_code=error_code_patch_apply,
            phase="patch_apply",
            trace_ctx=trace_ctx,
            exc=exc,
        )


def sanitize_patch_with_events(
    state: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    stage: str,
    trace_ctx: Optional[Dict[str, Any]],
    sanitize_patch: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]],
    emit_turn_phase_event: Callable[..., None],
    turn_flow_error: Callable[..., Exception],
    error_code_patch_sanitize: str,
    extractor_apply_stage: str = "",
) -> Dict[str, Any]:
    try:
        emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": stage})
        sanitized = sanitize_patch(state, patch)
        emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": stage, "result": "ok"})
        return sanitized
    except Exception as exc:
        emit_turn_phase_event(
            trace_ctx,
            phase="patch_sanitize",
            success=False,
            error_code=error_code_patch_sanitize,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"stage": stage},
        )
        if extractor_apply_stage:
            emit_turn_phase_event(
                trace_ctx,
                phase="extractor_patch_apply",
                success=False,
                error_code=error_code_patch_sanitize,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": extractor_apply_stage},
            )
        raise turn_flow_error(
            error_code=error_code_patch_sanitize,
            phase="patch_sanitize",
            trace_ctx=trace_ctx,
            exc=exc,
        )


def validate_patch_with_events(
    state: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    stage: str,
    trace_ctx: Optional[Dict[str, Any]],
    validate_patch: Callable[[Dict[str, Any], Dict[str, Any]], None],
    emit_turn_phase_event: Callable[..., None],
    turn_flow_error: Callable[..., Exception],
    error_code_schema_validation: str,
    extractor_apply_stage: str = "",
) -> None:
    try:
        emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": stage})
        validate_patch(state, patch)
        emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": stage, "result": "ok"})
    except Exception as exc:
        emit_turn_phase_event(
            trace_ctx,
            phase="schema_validation",
            success=False,
            error_code=error_code_schema_validation,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"stage": stage},
        )
        if extractor_apply_stage:
            emit_turn_phase_event(
                trace_ctx,
                phase="extractor_patch_apply",
                success=False,
                error_code=error_code_schema_validation,
                error_class=exc.__class__.__name__,
                message=str(exc)[:240],
                extra={"stage": extractor_apply_stage},
            )
        raise turn_flow_error(
            error_code=error_code_schema_validation,
            phase="schema_validation",
            trace_ctx=trace_ctx,
            exc=exc,
        )

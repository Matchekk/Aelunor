from typing import Any, Callable, Dict, Optional


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

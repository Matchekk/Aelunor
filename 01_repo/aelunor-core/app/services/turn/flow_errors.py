from typing import Any, Callable, Dict, Optional


def build_narrator_turn_error(
    message: str,
    *,
    trace_ctx: Optional[Dict[str, Any]],
    error_code_narrator_response: str,
    emit_turn_phase_event: Callable[..., None],
    turn_flow_error: Callable[..., Exception],
) -> Exception:
    emit_turn_phase_event(
        trace_ctx,
        phase="narrator_call_finished",
        success=False,
        error_code=error_code_narrator_response,
        error_class="NarratorGuardError",
        message=str(message)[:240],
    )
    return turn_flow_error(
        error_code=error_code_narrator_response,
        phase="narrator_call_finished",
        trace_ctx=trace_ctx,
        user_message=message,
    )

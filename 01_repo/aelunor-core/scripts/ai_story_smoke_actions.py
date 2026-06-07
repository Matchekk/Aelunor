from __future__ import annotations

from typing import Sequence


SMOKE_ACTOR = "slot_1"
SMOKE_PLAYER_ID = "player_smoke_host"
PREFERRED_SMOKE_ACTION_TYPES = ("do", "story", "say", "canon")


class SmokeRunFailure(Exception):
    def __init__(
        self,
        *,
        phase: str,
        scenario_key: str,
        turn_index: int | None = None,
        actor: str | None = None,
        action_type: str | None = None,
        available_action_types: Sequence[str] = (),
        original: BaseException | None = None,
        message: str | None = None,
    ) -> None:
        super().__init__(message or str(original) or phase)
        self.phase = phase
        self.scenario_key = scenario_key
        self.turn_index = turn_index
        self.actor = actor
        self.action_type = action_type
        self.available_action_types = tuple(available_action_types)
        self.original = original


def available_smoke_action_types(configured_action_types: Sequence[str] | None = None) -> tuple[str, ...]:
    if configured_action_types is None:
        from app.config.runtime import ACTION_TYPES

        configured_action_types = ACTION_TYPES
    return tuple(str(action_type).strip().lower() for action_type in configured_action_types if str(action_type).strip())


def resolve_smoke_action_type(
    requested_action_type: str | None = None,
    configured_action_types: Sequence[str] | None = None,
) -> str:
    available = available_smoke_action_types(configured_action_types)
    if not available:
        raise ValueError("No ACTION_TYPES are configured for AI story smoke turns.")

    if requested_action_type:
        normalized = str(requested_action_type).strip().lower()
        if normalized in available:
            return normalized
        raise ValueError(f"Action type '{requested_action_type}' is not configured.")

    for preferred in PREFERRED_SMOKE_ACTION_TYPES:
        if preferred in available:
            return preferred
    return available[0]


def format_smoke_failure(error: SmokeRunFailure) -> str:
    turn_part = f" turn={error.turn_index}" if error.turn_index is not None else ""
    lines = [f"AI Story Smoke abgebrochen in phase={error.phase} scenario={error.scenario_key}{turn_part}"]
    if error.actor:
        lines.append(f"Actor: {error.actor}")
    if error.action_type:
        lines.append(f"Action type: {error.action_type}")
    if error.available_action_types:
        lines.append(f"Available action types: {', '.join(error.available_action_types)}")
    if error.original is not None:
        lines.append(f"Original error type: {error.original.__class__.__name__}")
        lines.append(f"Original error: {error.original!r}")
    else:
        lines.append(f"Error: {error}")
    return "\n".join(lines)


def build_generic_smoke_failure(exc: BaseException, *, scenario_key: str) -> SmokeRunFailure:
    return SmokeRunFailure(phase="smoke_run", scenario_key=scenario_key, original=exc)

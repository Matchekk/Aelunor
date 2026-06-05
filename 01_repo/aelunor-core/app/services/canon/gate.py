from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional

from app.config.canon import CANON_GATE_ACTIVE_DOMAINS, CANON_GATE_DOMAINS_SUPPORTED
from app.config.errors import ERROR_CODE_EXTRACTOR, ERROR_CODE_PATCH_APPLY
from app.core.ids import deep_copy
from app.services.campaigns.party import display_name_for_slot
from app.services.canon import patch_gate
from app.services.canon.progression_gate import (
    call_progression_canon_extractor,
    detect_progression_claim_types,
    merge_progression_patch_additive,
    normalize_progression_extractor_character_patch,
    progression_claim_coverage_for_actor_patch,
    progression_claim_text_for_actor,
    progression_missing_claim_types,
)
from app.services.patch_payloads import normalize_patch_semantics


def _noop_emit_turn_phase_event(*_args: Any, **_kwargs: Any) -> None:
    return None


@dataclass(frozen=True)
class CanonGateDependencies:
    emit_turn_phase_event: Callable[..., None] = _noop_emit_turn_phase_event


_DEPS = CanonGateDependencies()


def configure(**overrides: Callable[..., Any]) -> None:
    global _DEPS
    valid = {key: value for key, value in overrides.items() if hasattr(_DEPS, key) and value is not None}
    if valid:
        _DEPS = replace(_DEPS, **valid)


def emit_turn_phase_event(*args: Any, **kwargs: Any) -> None:
    _DEPS.emit_turn_phase_event(*args, **kwargs)


def run_canon_gate(
    campaign: Dict[str, Any],
    *,
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    story_text: str,
    trace_ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    merged_patch = normalize_patch_semantics(patch)
    gate_meta: Dict[str, Any] = {
        "domains_supported": list(CANON_GATE_DOMAINS_SUPPORTED),
        "domains_active": sorted(CANON_GATE_ACTIVE_DOMAINS),
        "domains_run": [],
        "claim_types": [],
        "missing_claim_types": [],
        "decision": "skipped",
        "reason_code": "NO_ACTION",
        "extractor_confidence": "low",
        "extractor_confidence_score": 0.0,
        "needs_review": False,
        "warnings": [],
    }
    emit_turn_phase_event(
        trace_ctx,
        phase="canon_gate_started",
        success=True,
        extra={"domains_active": sorted(CANON_GATE_ACTIVE_DOMAINS)},
    )
    if action_type == "canon" or actor not in (state_after.get("characters") or {}):
        gate_meta["reason_code"] = "SKIPPED_MODE_OR_ACTOR"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    if "progression" not in CANON_GATE_ACTIVE_DOMAINS:
        gate_meta["reason_code"] = "DOMAIN_DISABLED"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    actor_display = display_name_for_slot(campaign, actor)
    claim_text = progression_claim_text_for_actor(story_text, actor_display)
    claim_types = detect_progression_claim_types(claim_text, actor_display)
    gate_meta["domains_run"] = ["progression"]
    gate_meta["claim_types"] = claim_types
    if not claim_types:
        gate_meta["reason_code"] = "NO_CLAIMS"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    coverage = progression_claim_coverage_for_actor_patch(merged_patch, actor)
    missing_claims = progression_missing_claim_types(claim_types, coverage)
    gate_meta["missing_claim_types"] = missing_claims
    if not missing_claims:
        gate_meta["reason_code"] = "STRUCTURED_ALREADY_PRESENT"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"], "claims": claim_types},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    emit_turn_phase_event(
        trace_ctx,
        phase="progression_extractor_started",
        success=True,
        extra={"claims": missing_claims},
    )
    try:
        extractor_result = call_progression_canon_extractor(
            campaign,
            state_after,
            actor=actor,
            action_type=action_type,
            claim_types=missing_claims,
            claim_text=claim_text,
            player_text=player_text,
            story_text=story_text,
        )
        emit_turn_phase_event(
            trace_ctx,
            phase="progression_extractor_finished",
            success=True,
            extra={
                "claims": missing_claims,
                "confidence": extractor_result.get("confidence"),
                "score": float(extractor_result.get("confidence_score", 0.0) or 0.0),
            },
        )
    except Exception as exc:
        warning = f"progression_extractor_error:{exc.__class__.__name__}"
        gate_meta["warnings"].append(warning)
        gate_meta["reason_code"] = "PROGRESSION_EXTRACTOR_ERROR"
        emit_turn_phase_event(
            trace_ctx,
            phase="progression_extractor_finished",
            success=False,
            error_code=ERROR_CODE_EXTRACTOR,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"claims": missing_claims},
        )
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"], "warnings": gate_meta["warnings"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    confidence = str(extractor_result.get("confidence") or "low").strip().lower()
    confidence_score = float(extractor_result.get("confidence_score", 0.0) or 0.0)
    gate_meta["extractor_confidence"] = confidence
    gate_meta["extractor_confidence_score"] = confidence_score
    gate_meta["extractor_model_confidence"] = str(extractor_result.get("model_confidence") or "")
    gate_meta["extractor_coverage"] = deep_copy(extractor_result.get("coverage") or [])
    character_patch = normalize_progression_extractor_character_patch(extractor_result.get("character_patch"))

    if confidence == "low" or not character_patch:
        gate_meta["reason_code"] = "LOW_CONFIDENCE_NO_COMMIT" if confidence == "low" else "EMPTY_EXTRACTOR_PATCH"
        gate_meta["decision"] = "skipped"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={
                "decision": gate_meta["decision"],
                "reason_code": gate_meta["reason_code"],
                "confidence": confidence,
                "score": confidence_score,
            },
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    merged_with_gate, merge_meta = merge_progression_patch_additive(
        base_patch=merged_patch,
        actor=actor,
        supplement_character_patch=character_patch,
        state_after=state_after,
    )
    gate_meta["merge"] = merge_meta
    if not (merge_meta.get("applied_keys") or []):
        gate_meta["decision"] = "skipped"
        gate_meta["reason_code"] = "NO_ADDITIVE_CHANGES"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    try:
        state_after, merged_patch = patch_gate.apply_canon_gate_patch(
            campaign,
            state_after=state_after,
            merged_patch=merged_patch,
            merged_with_gate=merged_with_gate,
            actor=actor,
            trace_ctx=trace_ctx,
        )
    except Exception as exc:
        gate_meta["decision"] = "skipped"
        gate_meta["reason_code"] = "GATE_PATCH_APPLY_FAILED"
        gate_meta["warnings"].append(f"gate_patch_apply_failed:{exc.__class__.__name__}")
        emit_turn_phase_event(
            trace_ctx,
            phase="patch_apply",
            success=False,
            error_code=ERROR_CODE_PATCH_APPLY,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"stage": "canon_gate"},
        )
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={
                "decision": gate_meta["decision"],
                "reason_code": gate_meta["reason_code"],
                "warnings": gate_meta["warnings"],
            },
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    gate_meta["decision"] = "flagged" if confidence == "medium" else "committed"
    gate_meta["needs_review"] = bool(confidence == "medium")
    gate_meta["reason_code"] = "COMMIT_MEDIUM_CONFIDENCE" if confidence == "medium" else "COMMIT_HIGH_CONFIDENCE"
    emit_turn_phase_event(
        trace_ctx,
        phase="canon_gate_finished",
        success=True,
        extra={
            "decision": gate_meta["decision"],
            "reason_code": gate_meta["reason_code"],
            "confidence": confidence,
            "score": confidence_score,
            "applied_keys": merge_meta.get("applied_keys") or [],
        },
    )
    return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

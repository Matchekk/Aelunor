"""Offline unit tests for the llama.cpp failure classifier (PHASE 2 core).

No LLM server required: we feed canned TurnObservation records and assert the
stage / severity mapping. This is what makes the sporadic fail *classifiable*
instead of chased by feel.
"""
from app.config.errors import (
    ERROR_CODE_JSON_REPAIR,
    ERROR_CODE_NARRATOR_RESPONSE,
    ERROR_CODE_PATCH_APPLY,
    ERROR_CODE_PATCH_SANITIZE,
    ERROR_CODE_SCHEMA_VALIDATION,
)
from benchmark.llama_failure_classifier import (
    LlmCallDiag,
    TurnObservation,
    TurnPhaseEvent,
    classify_turn,
    render_table,
    summarize,
    SEVERITY_DEGRADED,
    SEVERITY_FAIL,
    SEVERITY_OK,
    STAGE_A_EMPTY,
    STAGE_B_TRANSPORT,
    STAGE_C_INVALID_JSON,
    STAGE_D_REPAIR_FAILED,
    STAGE_E_SCHEMA,
    STAGE_F_AELUNOR_PATCH,
    STAGE_G_STORY,
    STAGE_H_PATCH_APPLY,
    STAGE_OK,
)


def _ok_call(**kw):
    base = dict(finish_reason="stop", content_len=900, has_schema=True, json_parse_ok=True)
    base.update(kw)
    return LlmCallDiag(**base)


def test_clean_turn_is_ok():
    obs = TurnObservation(
        turn=1, gm_text_usable=True, patch_usable=True, calls=[_ok_call()]
    )
    c = classify_turn(obs)
    assert c.stage == STAGE_OK
    assert c.severity == SEVERITY_OK
    assert c.is_clean


def test_empty_response_stage_a():
    obs = TurnObservation(
        turn=1,
        raised=True,
        message="Model returned empty content; nothing to repair",
        calls=[LlmCallDiag(finish_reason="stop", content_len=0, has_schema=True, json_parse_ok=False)],
    )
    c = classify_turn(obs)
    assert c.stage == STAGE_A_EMPTY
    assert c.severity == SEVERITY_FAIL


def test_transport_non200_stage_b():
    obs = TurnObservation(
        turn=1,
        raised=True,
        error_class="RuntimeError",
        message="llama.cpp error 500: internal",
        calls=[],
    )
    c = classify_turn(obs)
    assert c.stage == STAGE_B_TRANSPORT


def test_transport_timeout_stage_b():
    obs = TurnObservation(
        turn=1, raised=True, error_class="ReadTimeout", message="HTTPSConnectionPool timed out",
    )
    c = classify_turn(obs)
    assert c.stage == STAGE_B_TRANSPORT


def test_invalid_json_recovered_is_degraded_stage_c():
    # JSON was malformed but a formatless retry recovered -> DEGRADED, stage C.
    obs = TurnObservation(
        turn=1,
        gm_text_usable=True,
        patch_usable=True,
        calls=[
            LlmCallDiag(finish_reason="stop", content_len=400, has_schema=True, json_parse_ok=False, head="Sure! Here"),
            _ok_call(has_schema=False),
        ],
        events=[TurnPhaseEvent(phase="narrator_json_parse_repair", success=False, mode="parse_failed_repair_attempt"),
                TurnPhaseEvent(phase="narrator_json_parse_repair", success=True, mode="formatless_retry_ok")],
    )
    c = classify_turn(obs)
    assert c.stage == STAGE_C_INVALID_JSON
    assert c.severity == SEVERITY_DEGRADED


def test_repair_failed_stage_d():
    obs = TurnObservation(
        turn=1,
        raised=True,
        error_code=ERROR_CODE_JSON_REPAIR,
        message="repair failed",
        calls=[LlmCallDiag(finish_reason="length", content_len=6000, has_schema=True, json_parse_ok=False, head="{ \"story\":")],
        events=[TurnPhaseEvent(phase="narrator_json_parse_repair", success=False, mode="repair_failed")],
    )
    c = classify_turn(obs)
    assert c.stage == STAGE_D_REPAIR_FAILED
    assert c.severity == SEVERITY_FAIL
    assert c.truncated is True  # finish_reason=length surfaced


def test_schema_validation_stage_e():
    obs = TurnObservation(
        turn=1, raised=True, error_code=ERROR_CODE_SCHEMA_VALIDATION, message="missing 'patch'",
        calls=[_ok_call()],
    )
    assert classify_turn(obs).stage == STAGE_E_SCHEMA


def test_patch_sanitize_stage_f():
    obs = TurnObservation(
        turn=1, raised=True, error_code=ERROR_CODE_PATCH_SANITIZE, message="unknown op",
        calls=[_ok_call()],
    )
    assert classify_turn(obs).stage == STAGE_F_AELUNOR_PATCH


def test_story_guard_stage_g():
    obs = TurnObservation(
        turn=1, raised=True, error_code=ERROR_CODE_NARRATOR_RESPONSE, message="degenerate repetition",
        calls=[_ok_call()],
    )
    assert classify_turn(obs).stage == STAGE_G_STORY


def test_patch_apply_stage_h():
    obs = TurnObservation(
        turn=1, raised=True, error_code=ERROR_CODE_PATCH_APPLY, message="entity not found",
        calls=[_ok_call()],
    )
    assert classify_turn(obs).stage == STAGE_H_PATCH_APPLY


def test_upstream_precedence_empty_beats_repair_code():
    # An empty first call that also surfaced a repair error code is reported at
    # the most-upstream stage (A), not D.
    obs = TurnObservation(
        turn=1,
        raised=True,
        error_code=ERROR_CODE_JSON_REPAIR,
        message="Model returned empty content; nothing to repair",
        calls=[LlmCallDiag(content_len=0, has_schema=True, json_parse_ok=False)],
    )
    assert classify_turn(obs).stage == STAGE_A_EMPTY


def test_summarize_and_repro_grouping():
    obs_fail = TurnObservation(
        turn=1, raised=True, error_code=ERROR_CODE_JSON_REPAIR,
        calls=[LlmCallDiag(content_len=5000, json_parse_ok=False, head="oops")],
        events=[TurnPhaseEvent(mode="repair_failed", success=False)],
    )
    c1 = classify_turn(obs_fail)
    c2 = classify_turn(obs_fail)  # identical -> same repro_key
    ok = classify_turn(TurnObservation(turn=2, gm_text_usable=True, patch_usable=True, calls=[_ok_call()]))
    s = summarize([c1, c2, ok])
    assert s["total"] == 3
    assert s["hard_fails"] == 2
    assert s["by_severity"][SEVERITY_OK] == 1
    # identical fails collapse into one repro group with count 2
    assert s["repro_groups"][c1.repro_key] == 2


def test_render_table_no_fails():
    ok = classify_turn(TurnObservation(turn=1, gm_text_usable=True, patch_usable=True, calls=[_ok_call()]))
    table = render_table([ok])
    assert "keine" in table
    assert table.startswith("| Fail |")


def test_render_table_with_fail_has_fix_hint():
    obs = TurnObservation(
        turn=1, raised=True, error_code=ERROR_CODE_JSON_REPAIR,
        calls=[LlmCallDiag(content_len=5000, json_parse_ok=False, head="oops")],
        events=[TurnPhaseEvent(mode="repair_failed", success=False)],
    )
    table = render_table([classify_turn(obs)])
    assert STAGE_D_REPAIR_FAILED in table
    assert "repair" in table.lower()

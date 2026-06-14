"""Pure, offline-testable classifier for llama.cpp (and Ollama) turn failures.

PHASE 2 of the fast-brain-llama loop: the sporadic "1 in 4" llama.cpp
format/repair fail must become *reproducible and classifiable* instead of being
chased by feel. This module is the deterministic core — it takes a normalized
observation of one turn (the per-call LLM diagnostics plus the turn-phase
events the engine already emits) and maps it to exactly one failure stage.

It has **no** I/O and **no** LLM dependency, so it is unit-tested with canned
records. The harness ``diagnose_llama_cpp_failures.py`` collects the real
observations and feeds them here.

Stage vocabulary (mirrors the engine's parse/repair/validate pipeline in
``app/services/llm/client.py`` + ``app/services/turn_engine.py``):

    A  EMPTY_RESPONSE     model returned empty content (nothing to parse/repair)
    B  TRANSPORT_ADAPTER  HTTP/transport error or non-200 from the OpenAI adapter
    C  INVALID_JSON       content was non-JSON / malformed structured output
    D  JSON_REPAIR_FAILED json_repair + formatless retry could not recover JSON
    E  SCHEMA_VALIDATION  JSON parsed but failed schema validation
    F  AELUNOR_PATCH      patch sanitizer / Aelunor validator rejected the patch
    G  STORY_QUALITY      narrator/story/repetition guard rejected the prose
    H  PATCH_APPLY        patch/state validator could not apply the patch

Severity:

    OK        turn produced a usable result on the first structured call
    DEGRADED  turn recovered, but only via repair / formatless retry (soft fail)
    FAIL      turn produced no usable result (hard fail)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.config.errors import (
    ERROR_CODE_JSON_REPAIR,
    ERROR_CODE_NARRATOR_RESPONSE,
    ERROR_CODE_PATCH_APPLY,
    ERROR_CODE_PATCH_SANITIZE,
    ERROR_CODE_SCHEMA_VALIDATION,
)

# --- Stage table ----------------------------------------------------------

STAGE_A_EMPTY = "A"
STAGE_B_TRANSPORT = "B"
STAGE_C_INVALID_JSON = "C"
STAGE_D_REPAIR_FAILED = "D"
STAGE_E_SCHEMA = "E"
STAGE_F_AELUNOR_PATCH = "F"
STAGE_G_STORY = "G"
STAGE_H_PATCH_APPLY = "H"
STAGE_OK = "OK"

STAGE_LABELS = {
    STAGE_A_EMPTY: "empty response",
    STAGE_B_TRANSPORT: "transport / OpenAI adapter",
    STAGE_C_INVALID_JSON: "invalid JSON / malformed structured output",
    STAGE_D_REPAIR_FAILED: "json_repair failed",
    STAGE_E_SCHEMA: "schema validation failed",
    STAGE_F_AELUNOR_PATCH: "Aelunor patch validator rejected",
    STAGE_G_STORY: "story quality / repetition rejected",
    STAGE_H_PATCH_APPLY: "patch/state apply rejected",
    STAGE_OK: "ok",
}

# Hints surfaced in the classification table's "Fix-Kandidat" column. Kept here
# (not in the harness) so the mapping is reviewed alongside the stage logic.
STAGE_FIX_HINTS = {
    STAGE_A_EMPTY: "raise max_tokens / check finish_reason=length; warm model before run",
    STAGE_B_TRANSPORT: "server args / timeout / keep-alive; confirm /v1 reachable",
    STAGE_C_INVALID_JSON: "force response_format json_schema (strict grammar), not json_object",
    STAGE_D_REPAIR_FAILED: "give repair pass full token budget; lower temperature on retry",
    STAGE_E_SCHEMA: "tighten grammar schema; check optional-vs-required field drift",
    STAGE_F_AELUNOR_PATCH: "sanitizer allow-list / patch shape; compare vs Ollama output",
    STAGE_G_STORY: "story_length_guard threshold / repetition; check runaway tokens",
    STAGE_H_PATCH_APPLY: "state precondition / id resolution; inspect patch payload",
}

SEVERITY_OK = "OK"
SEVERITY_DEGRADED = "DEGRADED"
SEVERITY_FAIL = "FAIL"

_TRANSPORT_ERROR_CLASSES = {
    "ConnectionError",
    "ConnectTimeout",
    "ReadTimeout",
    "Timeout",
    "HTTPError",
    "RequestException",
    "RuntimeError",  # adapter raises RuntimeError("llama.cpp error <code>: ...")
}
_TRANSPORT_MESSAGE_MARKERS = (
    "llama.cpp error",
    "connection refused",
    "timed out",
    "max retries exceeded",
    "failed to establish",
)


# --- Observation model -----------------------------------------------------


@dataclass
class LlmCallDiag:
    """One LLM call as captured by the AELUNOR_LLM_DIAG hook in the adapter."""

    finish_reason: Optional[str] = None
    completion_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    content_len: int = 0
    has_schema: bool = False
    json_parse_ok: bool = False
    head: str = ""
    tail: str = ""

    @property
    def truncated(self) -> bool:
        return (self.finish_reason or "").lower() == "length"

    @property
    def empty(self) -> bool:
        return self.content_len <= 0


@dataclass
class TurnPhaseEvent:
    """A turn-phase event emitted by the engine (profiling jsonl)."""

    phase: str = ""
    success: bool = True
    error_code: Optional[str] = None
    error_class: Optional[str] = None
    mode: Optional[str] = None
    message: str = ""


@dataclass
class TurnObservation:
    """Everything we know about a single benchmarked turn."""

    turn: int = 0
    action: str = ""
    raised: bool = False
    error_class: Optional[str] = None
    error_code: Optional[str] = None
    message: str = ""
    gm_text_usable: bool = False
    patch_usable: bool = False
    calls: List[LlmCallDiag] = field(default_factory=list)
    events: List[TurnPhaseEvent] = field(default_factory=list)


@dataclass
class Classification:
    stage: str
    label: str
    severity: str
    truncated: bool
    repro_key: str
    fix_candidate: str
    evidence: str

    @property
    def is_fail(self) -> bool:
        return self.severity == SEVERITY_FAIL

    @property
    def is_clean(self) -> bool:
        return self.severity == SEVERITY_OK


# --- Helpers ---------------------------------------------------------------


def _event_codes(obs: TurnObservation) -> List[TurnPhaseEvent]:
    return [e for e in obs.events if not e.success]


def _has_mode(obs: TurnObservation, *modes: str) -> bool:
    wanted = set(modes)
    return any((e.mode or "") in wanted for e in obs.events)


def _looks_transport(error_class: Optional[str], message: str) -> bool:
    msg = (message or "").lower()
    if any(marker in msg for marker in _TRANSPORT_MESSAGE_MARKERS):
        return True
    # A bare RuntimeError only counts as transport when the message matches an
    # adapter transport marker (handled above); otherwise it is a logic error.
    if error_class and error_class in _TRANSPORT_ERROR_CLASSES and error_class != "RuntimeError":
        return True
    return False


def _repro_key(stage: str, obs: TurnObservation) -> str:
    """Stable key to group repeated identical failures across runs."""
    head = ""
    for call in obs.calls:
        if not call.json_parse_ok or call.empty:
            head = (call.head or "")[:40]
            break
    return f"{stage}:{obs.error_code or obs.error_class or 'guard'}:{head}".strip()


# --- Core classifier -------------------------------------------------------


def classify_turn(obs: TurnObservation) -> Classification:
    """Map a single turn observation to exactly one stage + severity.

    Precedence follows the pipeline order (most-upstream cause wins): a turn
    that fails schema validation *because* the JSON was malformed is reported
    at the JSON stage, not the schema stage. Recovery via repair/formatless
    retry downgrades a hard FAIL to DEGRADED rather than OK.
    """
    truncated = any(c.truncated for c in obs.calls)

    def build(stage: str, severity: str, evidence: str) -> Classification:
        return Classification(
            stage=stage,
            label=STAGE_LABELS[stage],
            severity=severity,
            truncated=truncated,
            repro_key=_repro_key(stage, obs),
            fix_candidate=STAGE_FIX_HINTS.get(stage, ""),
            evidence=evidence[:240],
        )

    # Clean, non-raising turn that produced a usable result.
    recovered = _has_mode(obs, "formatless_retry_ok", "repair_ok")
    if not obs.raised and obs.gm_text_usable and obs.patch_usable:
        if recovered:
            return build(
                _recovered_stage(obs),
                SEVERITY_DEGRADED,
                "usable result but only after repair/formatless retry",
            )
        return build(STAGE_OK, SEVERITY_OK, "first structured call usable")

    severity = SEVERITY_FAIL if obs.raised or not obs.gm_text_usable else SEVERITY_DEGRADED

    # A — empty response. Most upstream: nothing to parse.
    empty_call = any(c.empty for c in obs.calls)
    if empty_call or "empty content" in (obs.message or "").lower():
        return build(STAGE_A_EMPTY, severity, "model returned empty content")

    # B — transport / adapter (non-200, connection, timeout).
    if _looks_transport(obs.error_class, obs.message):
        return build(STAGE_B_TRANSPORT, severity, f"{obs.error_class}: {obs.message}")

    # C / D — JSON layer. Distinguish recovered (C) from unrecoverable (D).
    json_failed_call = any((not c.json_parse_ok) and not c.empty for c in obs.calls)
    repair_failed = (
        obs.error_code == ERROR_CODE_JSON_REPAIR
        or _has_mode(obs, "repair_failed", "formatless_retry_failed")
    )
    if repair_failed and (obs.raised or not obs.gm_text_usable):
        return build(STAGE_D_REPAIR_FAILED, severity, "repair + formatless retry exhausted")
    if json_failed_call:
        # JSON was malformed but the turn still produced usable output -> the
        # repair path saved it; report the upstream cause as DEGRADED.
        return build(STAGE_C_INVALID_JSON, severity, "non-JSON / malformed structured output")

    # E — schema validation.
    if obs.error_code == ERROR_CODE_SCHEMA_VALIDATION:
        return build(STAGE_E_SCHEMA, severity, obs.message or "schema validation rejected")

    # F — Aelunor patch sanitizer / validator.
    if obs.error_code == ERROR_CODE_PATCH_SANITIZE:
        return build(STAGE_F_AELUNOR_PATCH, severity, obs.message or "patch sanitizer rejected")

    # G — story quality / repetition / degenerate narrator.
    if obs.error_code == ERROR_CODE_NARRATOR_RESPONSE:
        return build(STAGE_G_STORY, severity, obs.message or "story/repetition guard rejected")

    # H — patch apply against state.
    if obs.error_code == ERROR_CODE_PATCH_APPLY:
        return build(STAGE_H_PATCH_APPLY, severity, obs.message or "patch apply rejected")

    # Fell through: a fail we could not attribute. Surface honestly rather than
    # silently calling it OK.
    return build(
        STAGE_B_TRANSPORT if obs.error_class else STAGE_OK,
        severity,
        f"unattributed: {obs.error_class or ''} {obs.error_code or ''} {obs.message}".strip(),
    )


def _recovered_stage(obs: TurnObservation) -> str:
    """For a DEGRADED (recovered) turn, name the layer it recovered from."""
    if any(c.empty for c in obs.calls):
        return STAGE_A_EMPTY
    if any((not c.json_parse_ok) and not c.empty for c in obs.calls):
        return STAGE_C_INVALID_JSON
    return STAGE_C_INVALID_JSON


def summarize(classifications: List[Classification]) -> dict:
    """Aggregate counts for a run: totals by stage + severity + repro groups."""
    by_stage: dict = {}
    by_severity = {SEVERITY_OK: 0, SEVERITY_DEGRADED: 0, SEVERITY_FAIL: 0}
    repro: dict = {}
    for c in classifications:
        by_stage[c.stage] = by_stage.get(c.stage, 0) + 1
        by_severity[c.severity] = by_severity.get(c.severity, 0) + 1
        if c.severity != SEVERITY_OK:
            repro[c.repro_key] = repro.get(c.repro_key, 0) + 1
    return {
        "total": len(classifications),
        "by_stage": by_stage,
        "by_severity": by_severity,
        "repro_groups": repro,
        "hard_fails": by_severity.get(SEVERITY_FAIL, 0),
        "degraded": by_severity.get(SEVERITY_DEGRADED, 0),
    }


def render_table(classifications: List[Classification]) -> str:
    """Render the PHASE 2 deliverable table:
    | Fail | Repro? | Klassifikation | Ursache | Fix-Kandidat |
    """
    counts: dict = {}
    rows: dict = {}
    for c in classifications:
        if c.severity == SEVERITY_OK:
            continue
        counts[c.repro_key] = counts.get(c.repro_key, 0) + 1
        rows[c.repro_key] = c
    lines = ["| Fail | Repro? | Klassifikation | Ursache | Fix-Kandidat |",
             "| --- | --- | --- | --- | --- |"]
    if not rows:
        lines.append("| (keine) | – | 0 Fails | – | – |")
        return "\n".join(lines)
    for key, c in sorted(rows.items()):
        n = counts[key]
        repro = f"{n}×" if n > 1 else "1× (sporadisch)"
        klass = f"{c.stage} {c.label} [{c.severity}]"
        cause = c.evidence.replace("\n", " ")[:80] or "–"
        lines.append(f"| {key[:36]} | {repro} | {klass} | {cause} | {c.fix_candidate} |")
    return "\n".join(lines)

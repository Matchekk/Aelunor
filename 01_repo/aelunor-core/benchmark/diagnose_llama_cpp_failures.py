"""PHASE 2 diagnostic harness: make the sporadic llama.cpp fail reproducible.

Drives N real turns through the identical engine path as the API
(``turn_engine.create_turn_record``) against a chosen provider, captures the
per-call LLM diagnostics (``AELUNOR_LLM_DIAG``) plus any ``TurnFlowError``, and
classifies every turn into a failure stage via ``llama_failure_classifier``.

Privacy / repo hygiene:
  * Raw responses + prompt heads live ONLY in the gitignored
    ``benchmark/perf_results/diag/`` directory. Nothing here is committed.
  * Only sha8 + short head/tail are stored, never full prompts.

Usage:
  # 1) llama.cpp, 10 turns
  python benchmark/diagnose_llama_cpp_failures.py --provider llama_cpp_openai --turns 10 --label llama_t10
  # 2) on 0 fails: 20 turns
  python benchmark/diagnose_llama_cpp_failures.py --provider llama_cpp_openai --turns 20 --label llama_t20
  # 4) isolate one action and repeat it 10x
  python benchmark/diagnose_llama_cpp_failures.py --provider llama_cpp_openai --repeat-action 2 --turns 10 --label iso2
  # 5) same input against Ollama for comparison
  python benchmark/diagnose_llama_cpp_failures.py --provider ollama --turns 10 --label ollama_t10
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parents[1]
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from benchmark.llama_failure_classifier import (  # noqa: E402
    Classification,
    LlmCallDiag,
    TurnObservation,
    classify_turn,
    render_table,
    summarize,
)
from benchmark.run_turn_benchmark import (  # noqa: E402
    BENCH_DATA_DIR,
    DEFAULT_ACTIONS,
    DEFAULT_CAMPAIGN_SRC,
    RESULTS_DIR,
    ResourceSampler,
    aggregate_profiles,
    prepare_bench_runtime,
)

DIAG_DIR = RESULTS_DIR / "diag"  # gitignored (parent perf_results is ignored)


def _read_diag_calls(diag_path: Path) -> list[LlmCallDiag]:
    """Parse the per-call records the adapter wrote during one turn."""
    calls: list[LlmCallDiag] = []
    if not diag_path.exists():
        return calls
    for line in diag_path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        calls.append(
            LlmCallDiag(
                finish_reason=rec.get("finish_reason"),
                completion_tokens=rec.get("completion_tokens"),
                prompt_tokens=rec.get("prompt_tokens"),
                content_len=int(rec.get("content_len") or 0),
                has_schema=bool(rec.get("has_schema")),
                json_parse_ok=bool(rec.get("json_parse_ok")),
                head=str(rec.get("head") or ""),
                tail=str(rec.get("tail") or ""),
            )
        )
    return calls


def _observe_turn(turn_engine, state_engine, campaign, actor, player_id, *, index, action, diag_path) -> TurnObservation:
    if diag_path.exists():
        diag_path.unlink()
    obs = TurnObservation(turn=index, action=action)
    try:
        turn = turn_engine.create_turn_record(
            campaign=campaign,
            actor=actor,
            player_id=player_id,
            action_type="do",
            content=action,
            trace_ctx={"trace_id": f"diag_{index}"},
        )
        state_engine.save_campaign(campaign, reason="llm_diag")
        gm_text = str(turn.get("gm_text_display") or turn.get("gm_text_raw") or "")
        obs.gm_text_usable = len(gm_text.strip()) > 0
        # The engine raises on hard patch-apply failure, so a returned turn
        # means the patch was applied.
        obs.patch_usable = obs.gm_text_usable
    except Exception as exc:  # noqa: BLE001 — diagnostic harness must keep going
        obs.raised = True
        obs.error_class = type(exc).__name__
        obs.error_code = getattr(exc, "error_code", None)
        cause = getattr(exc, "cause_message", "") or str(exc)
        obs.message = f"{getattr(exc, 'phase', '')}: {cause}".strip(": ")
    obs.calls = _read_diag_calls(diag_path)
    return obs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--turns", type=int, default=10)
    parser.add_argument("--provider", default="llama_cpp_openai",
                        help="ollama | llama_cpp_openai")
    parser.add_argument("--second-brain", action="store_true")
    parser.add_argument("--repeat-action", type=int, default=None,
                        help="Isolate one DEFAULT_ACTIONS index and repeat it every turn.")
    parser.add_argument("--campaign-src", default=str(DEFAULT_CAMPAIGN_SRC))
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--llama-cpp-url", default="http://127.0.0.1:8088/v1")
    parser.add_argument("--llama-cpp-model", default="gemma-3n-e4b")
    args = parser.parse_args()

    campaign_src = Path(args.campaign_src)
    if not campaign_src.exists():
        print(f"Quell-Kampagne fehlt: {campaign_src}", file=sys.stderr)
        return 2

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    diag_path = DIAG_DIR / f"{args.label}_calls.jsonl"
    profile_path = DIAG_DIR / f"{args.label}_profile.jsonl"
    report_path = DIAG_DIR / f"{args.label}_classified.json"

    campaign_id = prepare_bench_runtime(campaign_src)
    os.environ["DATA_DIR"] = str(BENCH_DATA_DIR)
    os.environ["AELUNOR_PROFILE_TURNS"] = "1"
    os.environ["AELUNOR_PROFILE_PATH"] = str(profile_path)
    os.environ["OLLAMA_URL"] = args.ollama_url
    os.environ["AELUNOR_SECOND_BRAIN"] = "1" if args.second_brain else ""
    os.environ["AELUNOR_LLM_PROVIDER"] = args.provider
    os.environ["AELUNOR_LLM_DIAG"] = str(diag_path)
    if args.provider in ("llama_cpp_openai", "llama_cpp", "llamacpp"):
        os.environ["LLAMA_CPP_BASE_URL"] = args.llama_cpp_url
        os.environ["LLAMA_CPP_MODEL"] = args.llama_cpp_model
    for stale in (profile_path, diag_path):
        if stale.exists():
            stale.unlink()

    from app import main as app_main
    from app.services import state_engine, turn_engine

    turn_engine.configure(app_main.__dict__)
    state_engine.ensure_campaign_storage()
    campaign = state_engine.load_campaign(campaign_id)
    claims = campaign.get("claims") or {}
    actor = next(iter(claims), "slot_1")
    player_id = claims.get(actor, "")

    print(f"[diag:{args.label}] provider={args.provider} SB={'on' if args.second_brain else 'off'} "
          f"turns={args.turns} repeat_action={args.repeat_action}", flush=True)

    sampler = ResourceSampler()
    sampler.start()
    classifications: list[Classification] = []
    observations: list[dict] = []
    turn_times: list[float] = []
    for index in range(1, args.turns + 1):
        if args.repeat_action is not None:
            action = DEFAULT_ACTIONS[args.repeat_action % len(DEFAULT_ACTIONS)]
        else:
            action = DEFAULT_ACTIONS[(index - 1) % len(DEFAULT_ACTIONS)]
        t0 = time.perf_counter()
        obs = _observe_turn(
            turn_engine, state_engine, campaign, actor, player_id,
            index=index, action=action, diag_path=diag_path,
        )
        elapsed = time.perf_counter() - t0
        turn_times.append(elapsed)
        c = classify_turn(obs)
        classifications.append(c)
        flag = "OK " if c.is_clean else ("FAIL" if c.is_fail else "DEGR")
        print(f"  turn {index:>2}/{args.turns}  {elapsed:6.1f}s  [{flag}] {c.stage} {c.label}", flush=True)
        observations.append({
            "turn": index,
            "elapsed_s": round(elapsed, 1),
            "stage": c.stage,
            "severity": c.severity,
            "truncated": c.truncated,
            "repro_key": c.repro_key,
            "evidence": c.evidence,
            "calls": [vars(call) for call in obs.calls],
            "error_code": obs.error_code,
            "error_class": obs.error_class,
        })
    resources = sampler.stop()

    summ = summarize(classifications)
    table = render_table(classifications)
    report = {
        "label": args.label,
        "provider": args.provider,
        "second_brain": bool(args.second_brain),
        "turns": args.turns,
        "repeat_action": args.repeat_action,
        "summary": summ,
        "turn_times_s": [round(t, 1) for t in turn_times],
        "resources": resources,
        "phase_breakdown": aggregate_profiles(profile_path),
        "observations": observations,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Klassifikation ===", flush=True)
    print(table, flush=True)
    print(f"\nhard_fails={summ['hard_fails']} degraded={summ['degraded']} "
          f"ok={summ['by_severity'].get('OK', 0)}  -> {report_path}", flush=True)
    return 0 if summ["hard_fails"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Turn-Latency-Benchmark auf einer Kopie einer echten Kampagne.

Laeuft komplett ausserhalb der App-Laufzeit: kopiert eine Quell-Kampagne in
ein isoliertes Benchmark-DATA_DIR, fuehrt N echte Turns ueber
turn_engine.create_turn_record aus (identischer Pfad wie die API) und sammelt
pro Turn das Profiling-JSONL (AELUNOR_PROFILE_TURNS) plus GPU/RAM-Samples.

Jeder Lauf startet vom identischen Kampagnenstand -> A/B-vergleichbar.

Beispiel:
  python benchmark/run_turn_benchmark.py --label baseline --turns 4
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parents[1]
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

DEFAULT_CAMPAIGN_SRC = CORE_ROOT / ".agent_tmp" / "dev-runtime" / "campaigns" / "camp_c02276e6d5.json"
BENCH_DATA_DIR = CORE_ROOT / ".agent_tmp" / "perf-runtime"
RESULTS_DIR = CORE_ROOT / "benchmark" / "perf_results"

# Szenen-neutrale Aktionen, damit jeder Lauf unabhaengig vom genauen
# Story-Stand dieselben Inputs bekommt.
DEFAULT_ACTIONS = [
    "Ich sehe mich aufmerksam um und praege mir alle Details der Umgebung ein.",
    "Ich gehe vorsichtig weiter und achte auf Geraeusche oder Bewegungen.",
    "Ich untersuche das Auffaelligste in meiner Naehe genauer.",
    "Ich halte kurz inne, sammle mich und plane meinen naechsten Schritt.",
    "Ich setze meinen Weg fort und bleibe wachsam.",
]


class ResourceSampler(threading.Thread):
    def __init__(self, interval_s: float = 2.0) -> None:
        super().__init__(daemon=True)
        self.interval_s = interval_s
        self.samples: list[dict] = []
        self._stop = threading.Event()

    def run(self) -> None:
        try:
            import psutil  # type: ignore
        except ImportError:
            psutil = None
        while not self._stop.is_set():
            sample: dict = {"t": time.time()}
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=10,
                )
                if out.returncode == 0 and out.stdout.strip():
                    mem, util = out.stdout.strip().splitlines()[0].split(",")
                    sample["vram_mb"] = float(mem.strip())
                    sample["gpu_pct"] = float(util.strip())
            except (OSError, subprocess.SubprocessError, ValueError):
                pass
            if psutil is not None:
                sample["ram_mb"] = psutil.virtual_memory().used / (1024 * 1024)
                sample["cpu_pct"] = psutil.cpu_percent(interval=None)
            self.samples.append(sample)
            self._stop.wait(self.interval_s)

    def stop(self) -> dict:
        self._stop.set()
        self.join(timeout=5)
        def col(key: str) -> list[float]:
            return [s[key] for s in self.samples if key in s]
        summary = {}
        for key, agg in (("vram_mb", max), ("ram_mb", max), ("gpu_pct", statistics.mean), ("cpu_pct", statistics.mean)):
            values = col(key)
            if values:
                summary[f"{key}_{'peak' if agg is max else 'avg'}"] = round(agg(values), 1)
        return summary


def prepare_bench_runtime(campaign_src: Path) -> str:
    campaigns_dir = BENCH_DATA_DIR / "campaigns"
    if campaigns_dir.exists():
        shutil.rmtree(campaigns_dir)
    campaigns_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(campaign_src, campaigns_dir / campaign_src.name)
    settings_src = campaign_src.parents[1] / "llm_settings.json"
    if settings_src.exists():
        shutil.copy2(settings_src, BENCH_DATA_DIR / "llm_settings.json")
    return campaign_src.stem


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="Name des Laufs, bestimmt Ergebnisdateien")
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument("--campaign-src", default=str(DEFAULT_CAMPAIGN_SRC))
    parser.add_argument("--action-type", default="do")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument(
        "--provider",
        default="ollama",
        help="LLM provider: ollama | llama_cpp_openai (sets AELUNOR_LLM_PROVIDER).",
    )
    parser.add_argument(
        "--llama-cpp-url",
        default="http://127.0.0.1:8088/v1",
        help="llama.cpp OpenAI base URL (used when --provider llama_cpp_openai).",
    )
    parser.add_argument("--llama-cpp-model", default="gemma-3n-e4b")
    args = parser.parse_args()

    campaign_src = Path(args.campaign_src)
    if not campaign_src.exists():
        print(f"Quell-Kampagne fehlt: {campaign_src}", file=sys.stderr)
        return 2

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = RESULTS_DIR / f"{args.label}.jsonl"
    summary_path = RESULTS_DIR / f"{args.label}_summary.json"

    campaign_id = prepare_bench_runtime(campaign_src)

    os.environ["DATA_DIR"] = str(BENCH_DATA_DIR)
    os.environ["AELUNOR_PROFILE_TURNS"] = "1"
    os.environ["AELUNOR_PROFILE_PATH"] = str(profile_path)
    os.environ["OLLAMA_URL"] = args.ollama_url
    # LLM provider selection (read at import by app.adapters.llm_config).
    os.environ["AELUNOR_LLM_PROVIDER"] = args.provider
    if args.provider in ("llama_cpp_openai", "llama_cpp", "llamacpp"):
        os.environ["LLAMA_CPP_BASE_URL"] = args.llama_cpp_url
        os.environ["LLAMA_CPP_MODEL"] = args.llama_cpp_model
    if profile_path.exists():
        profile_path.unlink()

    from app import main as app_main
    from app.services import state_engine, turn_engine

    turn_engine.configure(app_main.__dict__)
    state_engine.ensure_campaign_storage()
    campaign = state_engine.load_campaign(campaign_id)
    claims = campaign.get("claims") or {}
    actor = next(iter(claims), "slot_1")
    player_id = claims.get(actor, "")

    sampler = ResourceSampler()
    sampler.start()
    turn_times: list[float] = []
    errors: list[str] = []
    stories: list[dict] = []
    for index in range(1, args.turns + 1):
        action = DEFAULT_ACTIONS[(index - 1) % len(DEFAULT_ACTIONS)]
        print(f"[{args.label}] Turn {index}/{args.turns}: {action[:60]}...", flush=True)
        t0 = time.perf_counter()
        try:
            turn = turn_engine.create_turn_record(
                campaign=campaign,
                actor=actor,
                player_id=player_id,
                action_type=args.action_type,
                content=action,
                trace_ctx={"trace_id": f"bench_{args.label}_{index}"},
            )
            state_engine.save_campaign(campaign, reason="perf_benchmark")
        except Exception as exc:  # noqa: BLE001 - Benchmark soll weiterlaufen
            errors.append(f"turn {index}: {type(exc).__name__}: {exc}")
            print(f"  FEHLER: {exc}", flush=True)
            continue
        elapsed = time.perf_counter() - t0
        turn_times.append(elapsed)
        stories.append({"turn": index, "action": action, "gm_text": str(turn.get("gm_text_display") or turn.get("gm_text_raw") or "")})
        print(f"  fertig in {elapsed:.1f}s", flush=True)

    resources = sampler.stop()

    summary = {
        "label": args.label,
        "campaign_id": campaign_id,
        "turns_requested": args.turns,
        "turns_completed": len(turn_times),
        "errors": errors,
        "turn_times_s": [round(t, 1) for t in turn_times],
        "total_avg_s": round(statistics.mean(turn_times), 1) if turn_times else None,
        "total_median_s": round(statistics.median(turn_times), 1) if turn_times else None,
        "best_s": round(min(turn_times), 1) if turn_times else None,
        "worst_s": round(max(turn_times), 1) if turn_times else None,
        "resources": resources,
        "env": {
            key: os.environ.get(key, "")
            for key in (
                "OLLAMA_MODEL", "OLLAMA_NUM_CTX", "OLLAMA_NARRATOR_MODEL", "OLLAMA_NARRATOR_NUM_CTX",
                "OLLAMA_EXTRACTOR_MODEL", "OLLAMA_EXTRACTOR_NUM_CTX", "OLLAMA_REPAIR_MODEL",
                "OLLAMA_REPAIR_NUM_CTX", "AELUNOR_CANON_EXTRACTOR_MODE",
                "AELUNOR_LLM_PROVIDER", "LLAMA_CPP_MODEL", "LLAMA_CPP_BASE_URL",
            )
        },
        "phase_breakdown": aggregate_profiles(profile_path),
        "state_digest": state_digest(campaign),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    stories_path = RESULTS_DIR / f"{args.label}_stories.json"
    stories_path.write_text(json.dumps(stories, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if turn_times and not errors else 1


def state_digest(campaign: dict) -> dict:
    """Kompakter Zustandsabdruck fuer Qualitaets-/Regressionsvergleich zwischen Laeufen."""
    state = campaign.get("state") or {}
    characters = state.get("characters") or {}
    slot = characters.get("slot_1") or {}
    inventory = slot.get("inventory") or []
    return {
        "meta_turn": (state.get("meta") or {}).get("turn"),
        "items_total": len(state.get("items") or {}),
        "npc_codex_total": len(state.get("npc_codex") or {}),
        "scenes_total": len(state.get("scenes") or {}),
        "slot1_scene": slot.get("scene_id"),
        "slot1_inventory_count": len(inventory) if isinstance(inventory, list) else None,
        "slot1_skills": sorted((slot.get("skills") or {}).keys()),
        "slot1_hp": slot.get("hp"),
        "slot1_xp": slot.get("xp"),
        "quarantine_count": len(((state.get("extraction_quarantine") or {}).get("entries") or [])
                                if isinstance(state.get("extraction_quarantine"), dict)
                                else (state.get("extraction_quarantine") or [])),
    }


def aggregate_profiles(profile_path: Path) -> dict:
    if not profile_path.exists():
        return {}
    phase_calls: dict[str, list[float]] = {}
    prompt_tokens: dict[str, list[int]] = {}
    nonllm_phases: dict[str, list[float]] = {}
    schema_fails = 0
    totals: list[float] = []
    for line in profile_path.read_text(encoding="utf-8").splitlines():
        try:
            report = json.loads(line)
        except json.JSONDecodeError:
            continue
        if report.get("kind") != "turn_profile":
            continue
        totals.append(float(report.get("total_s") or 0))
        per_phase: dict[str, float] = {}
        for call in report.get("llm_calls") or []:
            phase = str(call.get("phase") or "unphased")
            per_phase[phase] = per_phase.get(phase, 0.0) + float(call.get("s") or 0)
            prompt_tokens.setdefault(phase, []).append(int(call.get("prompt_tokens") or 0))
        for phase, seconds in per_phase.items():
            phase_calls.setdefault(phase, []).append(seconds)
        # Non-LLM phase timings (e.g. story guard, retrieval, persistence).
        for entry in report.get("phases") or []:
            name = str(entry.get("name") or "")
            if name:
                nonllm_phases.setdefault(name, []).append(float(entry.get("s") or 0))
    breakdown = {
        phase: {
            "avg_s": round(statistics.mean(values), 1),
            "max_s": round(max(values), 1),
            "turns_with_calls": len(values),
            "avg_prompt_tokens": int(statistics.mean(prompt_tokens.get(phase) or [0])),
            "max_prompt_tokens": max(prompt_tokens.get(phase) or [0]),
        }
        for phase, values in sorted(phase_calls.items())
    }
    breakdown["_turn_total"] = {
        "avg_s": round(statistics.mean(totals), 1) if totals else 0,
        "turns": len(totals),
    }
    if nonllm_phases:
        breakdown["_phase_timings"] = {
            name: {
                "avg_ms": round(statistics.mean(values) * 1000, 1),
                "max_ms": round(max(values) * 1000, 1),
                "turns": len(values),
            }
            for name, values in sorted(nonllm_phases.items())
        }
    return breakdown


if __name__ == "__main__":
    raise SystemExit(main())

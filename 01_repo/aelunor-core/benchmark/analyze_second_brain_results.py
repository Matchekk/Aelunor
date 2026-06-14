"""Compare Second Brain OFF vs ON benchmark runs.

Reads the *_summary.json (+ *_stories.json) produced by run_turn_benchmark.py
and emits a compact A/B(/C) comparison as Markdown + JSON. Pure stdlib,
offline. Raw inputs/outputs live under benchmark/perf_results/ (gitignored);
fold the printed table into docs/performance/second-brain-benchmark.md.

Usage:
  python benchmark/analyze_second_brain_results.py \
      --labels sb_A_off sb_B_on sb_C_on_long
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "perf_results"
_WORD = re.compile(r"[a-zA-Z0-9äöüÄÖÜß]+")


def _load(label: str, suffix: str) -> dict | list | None:
    path = RESULTS_DIR / f"{label}{suffix}"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _tokens(text: str) -> set[str]:
    return set(w.lower() for w in _WORD.findall(text or ""))


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _phase(summary: dict, name: str) -> dict:
    return (summary.get("phase_breakdown") or {}).get(name) or {}


def _phase_timing_ms(summary: dict, name: str, key: str = "avg_ms") -> float | None:
    timings = (summary.get("phase_breakdown") or {}).get("_phase_timings") or {}
    entry = timings.get(name) or {}
    return entry.get(key)


def _story_metrics(stories: list | None) -> dict:
    if not stories:
        return {}
    texts = [str(s.get("gm_text") or "") for s in stories]
    lengths = [len(t) for t in texts]
    # Inter-turn repetition: max similarity to any earlier turn.
    reps = []
    for i in range(1, len(texts)):
        reps.append(max((_jaccard(texts[i], texts[j]) for j in range(i)), default=0.0))
    # A/B-question markers + truncation (no terminal punctuation).
    ab_questions = sum(1 for t in texts if t.count("?") >= 2)
    truncated = sum(1 for t in texts if t.strip() and t.strip()[-1] not in ".!?\"'»)")
    return {
        "turns": len(texts),
        "gm_chars_avg": round(statistics.mean(lengths), 0) if lengths else 0,
        "interturn_repetition_avg": round(statistics.mean(reps), 3) if reps else 0.0,
        "interturn_repetition_max": round(max(reps), 3) if reps else 0.0,
        "ab_question_turns": ab_questions,
        "possibly_truncated_turns": truncated,
    }


def _variant(label: str) -> dict:
    summary = _load(label, "_summary.json")
    stories = _load(label, "_stories.json")
    if not summary:
        return {"label": label, "missing": True}
    narrator = _phase(summary, "narrator")
    return {
        "label": label,
        "turns_completed": summary.get("turns_completed"),
        "errors": summary.get("errors") or [],
        "total_avg_s": summary.get("total_avg_s"),
        "narrator_avg_s": narrator.get("avg_s"),
        "narrator_avg_prompt_tokens": narrator.get("avg_prompt_tokens"),
        "narrator_max_prompt_tokens": narrator.get("max_prompt_tokens"),
        "brain_write_ms_avg": _phase_timing_ms(summary, "second_brain_write"),
        "brain_write_ms_max": _phase_timing_ms(summary, "second_brain_write", "max_ms"),
        "brain_retrieval_ms_avg": _phase_timing_ms(summary, "second_brain_retrieval"),
        "brain_retrieval_ms_max": _phase_timing_ms(summary, "second_brain_retrieval", "max_ms"),
        "story_guard_s": _phase(summary, "story_length_guard").get("avg_s")
        or _phase_timing_ms(summary, "story_length_guard"),
        "memory_summary_s": _phase(summary, "memory_summary").get("avg_s")
        or _phase_timing_ms(summary, "memory_summary"),
        "vram_peak_mb": (summary.get("resources") or {}).get("vram_mb_peak"),
        "brain_digest": summary.get("brain_digest") or {},
        "stories": _story_metrics(stories),
    }


def _fmt(value, nd=1) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{nd}f}"
    return str(value)


def build_markdown(variants: list[dict]) -> str:
    present = [v for v in variants if not v.get("missing")]
    if not present:
        return "No benchmark summaries found in benchmark/perf_results/.\n"
    off = next((v for v in present if v["label"].endswith("_off") or "_off" in v["label"]), None)
    on = next((v for v in present if v is not off and (v["brain_digest"] or {}).get("enabled")), None)
    lines: list[str] = ["### Second Brain — A/B benchmark results", ""]

    cols = ["metric"] + [v["label"] for v in present]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] + ["---:"] * len(present)) + "|")

    def row(metric: str, key: str, nd=1):
        cells = [_fmt(v.get(key), nd) for v in present]
        lines.append(f"| {metric} | " + " | ".join(cells) + " |")

    row("turns completed", "turns_completed", 0)
    row("total avg s", "total_avg_s")
    row("narrator avg s", "narrator_avg_s")
    row("narrator avg prompt_tokens", "narrator_avg_prompt_tokens", 0)
    row("narrator max prompt_tokens", "narrator_max_prompt_tokens", 0)
    row("brain write ms (avg)", "brain_write_ms_avg")
    row("brain write ms (max)", "brain_write_ms_max")
    row("brain retrieval ms (avg)", "brain_retrieval_ms_avg")
    row("brain retrieval ms (max)", "brain_retrieval_ms_max")
    row("VRAM peak MB", "vram_peak_mb", 0)

    # story heuristics
    for metric, key in (
        ("gm chars avg", "gm_chars_avg"),
        ("inter-turn repetition avg", "interturn_repetition_avg"),
        ("inter-turn repetition max", "interturn_repetition_max"),
        ("A/B-question turns", "ab_question_turns"),
        ("possibly truncated turns", "possibly_truncated_turns"),
    ):
        cells = [_fmt((v.get("stories") or {}).get(key), 3) for v in present]
        lines.append(f"| {metric} | " + " | ".join(cells) + " |")

    # errors
    err_cells = [str(len(v.get("errors") or [])) for v in present]
    lines.append("| turn errors | " + " | ".join(err_cells) + " |")

    lines.append("")
    if off and on:
        a = off.get("narrator_avg_prompt_tokens") or 0
        b = on.get("narrator_avg_prompt_tokens") or 0
        delta = b - a
        lines.append(
            f"**brain_context_tokens ~= {delta:+.0f}** "
            f"(narrator avg prompt_tokens {on['label']} - {off['label']}; "
            f"the cost of the injected [RELEVANT_CAMPAIGN_BRAIN] block)."
        )
        bd = on.get("brain_digest") or {}
        counts = bd.get("counts") or {}
        entity = sum(counts.get(k, 0) for k in ("npc", "location", "item", "character", "faction", "concept"))
        lines.append(
            f"Brain after ON run: events={counts.get('event')} facts={counts.get('fact', 0)} "
            f"entities={entity} edges={counts.get('edges')} "
            f"open_threads={counts.get('open_thread')} failed_jobs={bd.get('failed_jobs')}. "
            f"(raw kinds: {dict((k, v) for k, v in counts.items())})"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", nargs="+", default=["sb_A_off", "sb_B_on", "sb_C_on_long"])
    parser.add_argument("--out-md", default=str(RESULTS_DIR / "second_brain_compare.md"))
    parser.add_argument("--out-json", default=str(RESULTS_DIR / "second_brain_compare.json"))
    args = parser.parse_args()

    variants = [_variant(label) for label in args.labels]
    markdown = build_markdown(variants)
    Path(args.out_md).write_text(markdown, encoding="utf-8")
    Path(args.out_json).write_text(json.dumps(variants, indent=2, ensure_ascii=False), encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

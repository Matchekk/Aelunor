from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.ai_story_smoke_scenarios import SCENARIOS


DEFAULT_TURNS = 3
MAX_TURNS = 10
DEFAULT_PROVIDER = "anthropic"
SECRET_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual AI story smoke test for Aelunor world and character systems.")
    parser.add_argument("--provider", default=None, help="LLM provider for this run, e.g. anthropic or ollama.")
    parser.add_argument("--turns", type=int, default=DEFAULT_TURNS)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="dark-fantasy")
    parser.add_argument("--out", default=None)
    parser.add_argument("--action-type", default=None, help="Configured Aelunor turn action type to use for smoke turns.")
    parser.add_argument("--keep-campaign", action="store_true")
    parser.add_argument("--debug", "--traceback", dest="debug", action="store_true", help="Print full traceback on smoke failure.")
    return parser.parse_args(argv)


def resolve_provider(args: argparse.Namespace, env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    provider = args.provider or env.get("AELUNOR_LLM_PROVIDER") or env.get("LLM_PROVIDER") or DEFAULT_PROVIDER
    return str(provider or DEFAULT_PROVIDER).strip().lower()


def normalize_turn_count(value: Any) -> int:
    try:
        turns = int(value)
    except (TypeError, ValueError):
        turns = DEFAULT_TURNS
    return max(1, min(MAX_TURNS, turns))


def anthropic_key_present(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return any(str(env.get(key) or "").strip() for key in SECRET_KEYS)


def validate_provider_ready(provider: str, env: Mapping[str, str] | None = None) -> tuple[bool, str]:
    env = os.environ if env is None else env
    if provider != "anthropic":
        return True, ""
    if not anthropic_key_present(env):
        return False, "ANTHROPIC_API_KEY oder ANTHROPIC_AUTH_TOKEN fehlt. Claude-Smoke sauber abgebrochen."
    try:
        import anthropic  # noqa: F401
    except Exception:
        return False, "Das Python-Paket 'anthropic' ist nicht installiert. Claude-Smoke sauber abgebrochen."
    return True, ""


def configure_provider_environment(provider: str) -> None:
    os.environ["LLM_PROVIDER"] = provider
    if provider == "anthropic":
        os.environ.setdefault("ANTHROPIC_TIMEOUT_SEC", "120")


def render_smoke_report(data: dict[str, Any]) -> str:
    context = data.get("prompt_context_check") or {}
    lines = [
        "# AI Story Smoke Report",
        "",
        f"Provider: {_clean(data.get('provider'))}",
        f"Model: {_clean(data.get('model'))}",
        f"Scenario: {_clean(data.get('scenario'))}",
        f"Campaign ID: {_clean(data.get('campaign_id'))}",
        f"Turns requested: {int(data.get('turns_requested') or 0)}",
        f"Turns completed: {int(data.get('turns_completed') or 0)}",
        "",
        "## World Bible Quality",
        _excerpt(data.get("world_bible_quality_markdown"), 2200) or "No World Bible Quality data.",
        "",
        "## Entity Guard Summary",
        _excerpt(data.get("entity_guard_markdown"), 2200) or "No Entity Guard data.",
        "",
        "## Prompt Context Check",
        f"- World Bible Summary injected: {_yes_no(context.get('world_bible_summary'))}",
        f"- Living Profile Summary injected: {_yes_no(context.get('living_profile_summary'))}",
        f"- Style Guard injected: {_yes_no(context.get('style_guard'))}",
        "",
        "## Sample Generated Names",
    ]
    names = [str(name) for name in (data.get("sample_generated_names") or []) if str(name).strip()]
    lines.extend(f"- {_clean(name)}" for name in names[:20])
    if not names:
        lines.append("- Keine benannten Entities im kompakten Patch-Report gefunden.")
    lines.extend(["", "## Potential Problems"])
    problems = [str(problem) for problem in (data.get("potential_problems") or []) if str(problem).strip()]
    lines.extend(f"- {_clean(problem)}" for problem in problems[:20])
    if not problems:
        lines.append("- Keine offensichtlichen Probleme im Smoke-Report.")
    lines.extend(["", "## Turn Samples"])
    for index, sample in enumerate(data.get("turn_samples") or [], start=1):
        lines.extend(
            [
                f"### Turn {index}",
                f"Player Action: {_clean(sample.get('player_action'))}",
                "GM Output excerpt:",
                _excerpt(sample.get("gm_output_excerpt"), 900) or "-",
                "Entity Guard Findings:",
            ]
        )
        findings = sample.get("entity_guard_findings") or []
        lines.extend(f"- {_clean(finding)}" for finding in findings[:8]) if findings else lines.append("- Keine Findings.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def turn_sample(action: str, turn: dict[str, Any]) -> dict[str, Any]:
    return {
        "player_action": action,
        "gm_output_excerpt": _excerpt(turn.get("gm_text_display") or turn.get("gm_text_raw"), 900),
        "entity_guard_findings": guard_findings(turn.get("entity_guard")),
    }


def guard_findings(entity_guard: Any) -> list[str]:
    findings: list[str] = []
    if not isinstance(entity_guard, dict):
        return findings
    for stage in ("narrator", "extractor", "merged"):
        report = entity_guard.get(stage)
        if not isinstance(report, dict):
            continue
        for entry in (report.get("reports") or [])[:8]:
            if not isinstance(entry, dict):
                continue
            status = str(entry.get("status") or "unknown")
            if status not in {"ok", "weak"}:
                findings.append(f"{stage}: {entry.get('entity_type', 'entity')} '{entry.get('name', '')}' -> {status}")
    return findings


def prompt_context_check(turns: list[dict[str, Any]]) -> dict[str, bool]:
    text = "\n".join(
        str(((turn.get("prompt_payload") or {}).get("world_character_context") or {}).get("combined_text") or "")
        for turn in turns
        if isinstance(turn, dict)
    )
    return {
        "world_bible_summary": "WORLD BIBLE SUMMARY" in text,
        "living_profile_summary": "ACTIVE CHARACTER LIVING SUMMARY" in text,
        "style_guard": "STYLE AND CONSISTENCY GUARD" in text,
    }


def sample_generated_names(turns: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for turn in turns:
        guard = turn.get("entity_guard") if isinstance(turn, dict) else {}
        for stage in ("narrator", "extractor", "merged"):
            report = guard.get(stage) if isinstance(guard, dict) else {}
            for entry in (report.get("reports") or []) if isinstance(report, dict) else []:
                name = str(entry.get("name") or "").strip()
                key = name.casefold()
                if name and key not in seen:
                    seen.add(key)
                    names.append(name)
    return names


def potential_problems(quality_review: dict[str, Any], guard_review: dict[str, Any], turns: list[dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    for row in quality_review.get("campaigns") or []:
        if int(row.get("score") or 0) < 70:
            problems.append(f"World Bible Quality niedrig: {row.get('score')}/100.")
        problems.extend(str(warning) for warning in (row.get("warnings") or [])[:6])
    distribution = ((guard_review.get("summary") or {}).get("status_distribution") or {})
    for status in ("generic", "forbidden", "needs_review"):
        count = int(distribution.get(status) or 0)
        if count:
            problems.append(f"Entity Guard meldet {count} {status}-Entities.")
    if not all(prompt_context_check(turns).values()):
        problems.append("Prompt Context Injection unvollstaendig.")
    return _unique(problems)


def model_for_provider(provider: str) -> str:
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", "")
    return os.getenv("ANTHROPIC_MODEL") or os.getenv("OLLAMA_MODEL") or ""


def default_report_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Path("reports") / f"ai_story_smoke_{stamp}.md"


def _excerpt(value: Any, max_chars: int) -> str:
    text = _clean(value)
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    for key in SECRET_KEYS:
        secret = os.getenv(key)
        if secret:
            text = text.replace(secret, "[redacted]")
    return re.sub(r"sk-ant-[A-Za-z0-9_-]+", "[redacted]", text)


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _unique(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = str(value).casefold()
        if value and key not in seen:
            seen.add(key)
            output.append(value)
    return output

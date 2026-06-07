from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Sequence

CORE_ROOT = Path(__file__).resolve().parents[1]
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from scripts.ai_story_smoke_scenarios import SCENARIOS, SmokeScenario
from scripts.ai_story_smoke_support import (
    MAX_TURNS,
    configure_provider_environment,
    default_report_path,
    model_for_provider,
    normalize_turn_count,
    parse_args,
    potential_problems,
    prompt_context_check,
    render_smoke_report,
    resolve_provider,
    sample_generated_names,
    turn_sample,
    validate_provider_ready,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    provider = resolve_provider(args)
    turns = normalize_turn_count(args.turns)
    ok, message = validate_provider_ready(provider)
    if not ok:
        print(message, file=sys.stderr)
        return 2
    configure_provider_environment(provider)
    print("WARNUNG: Dieser manuelle Smoke-Test nutzt echte LLM-Aufrufe und kann API-Kosten verursachen.", file=sys.stderr)
    try:
        report_data, campaign_path = run_story_smoke(provider=provider, scenario_key=args.scenario, turns=turns)
    except Exception as exc:
        print(f"AI Story Smoke abgebrochen: {exc}", file=sys.stderr)
        return 1
    out_path = Path(args.out) if args.out else default_report_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_smoke_report(report_data), encoding="utf-8")
    if campaign_path and not args.keep_campaign:
        try:
            Path(campaign_path).unlink(missing_ok=True)
        except OSError:
            pass
    print(f"AI Story Smoke Report geschrieben: {out_path}", file=sys.stderr)
    return 0


def run_story_smoke(*, provider: str, scenario_key: str, turns: int) -> tuple[dict[str, Any], Path | None]:
    from app import main as app_main
    from app.core.ids import hash_secret, make_id, utc_now
    from app.services import state_engine, turn_engine
    from app.services.characters.living_profile import generate_living_profile_fallback
    from app.services.world.world_bible import generate_world_bible_fallback
    from scripts.report_entity_guard import build_entity_guard_review, render_markdown_report as render_entity_guard_markdown
    from scripts.report_world_bible_quality import build_world_bible_quality_review, render_markdown_report as render_bible_quality_markdown

    scenario = SCENARIOS[scenario_key]
    turn_engine.configure(app_main.__dict__)
    state_engine.ensure_campaign_storage()
    campaign, campaign_path = _build_campaign(
        state_engine=state_engine,
        make_id=make_id,
        hash_secret=hash_secret,
        utc_now=utc_now,
        scenario=scenario,
        world_bible=generate_world_bible_fallback(scenario.setup_answers),
        living_profile_factory=generate_living_profile_fallback,
    )
    turn_samples: list[dict[str, Any]] = []
    completed = 0
    for action in scenario.actions[:turns]:
        turn = turn_engine.create_turn_record(
            campaign=campaign,
            actor="slot_1",
            player_id="player_smoke_host",
            action_type="play",
            content=action,
            trace_ctx={"trace_id": f"ai_smoke_{scenario.key}_{completed + 1}"},
        )
        completed += 1
        state_engine.save_campaign(campaign, reason="ai_story_smoke")
        turn_samples.append(turn_sample(action, turn))
    quality_review = build_world_bible_quality_review([campaign])
    guard_review = build_entity_guard_review([campaign])
    turns_payload = campaign.get("turns") or []
    return (
        {
            "provider": provider,
            "model": model_for_provider(provider),
            "scenario": scenario.key,
            "campaign_id": campaign.get("campaign_meta", {}).get("campaign_id", ""),
            "turns_requested": turns,
            "turns_completed": completed,
            "world_bible_quality_markdown": render_bible_quality_markdown(quality_review, limit=3),
            "entity_guard_markdown": render_entity_guard_markdown(guard_review, limit=20),
            "prompt_context_check": prompt_context_check(turns_payload),
            "sample_generated_names": sample_generated_names(turns_payload),
            "potential_problems": potential_problems(quality_review, guard_review, turns_payload),
            "turn_samples": turn_samples,
        },
        campaign_path,
    )


def _build_campaign(
    *,
    state_engine: Any,
    make_id: Any,
    hash_secret: Any,
    utc_now: Any,
    scenario: SmokeScenario,
    world_bible: dict[str, Any],
    living_profile_factory: Any,
) -> tuple[dict[str, Any], Path]:
    campaign_id = make_id("camp")
    now = utc_now()
    state = state_engine.deep_copy(state_engine.INITIAL_STATE)
    campaign = {
        "campaign_meta": {
            "campaign_id": campaign_id,
            "title": scenario.title,
            "join_code_hash": hash_secret("AI-SMOKE"),
            "host_player_id": "player_smoke_host",
            "created_at": now,
            "updated_at": now,
            "status": "active",
        },
        "players": {"player_smoke_host": _smoke_player(hash_secret, now)},
        "claims": {"slot_1": "player_smoke_host"},
        "state": state,
        "turns": [],
        "boards": state_engine.default_boards("player_smoke_host"),
        "setup": state_engine.default_setup(),
        "board_revisions": [],
        "legacy_migration": None,
    }
    _fill_setup(campaign, scenario)
    character = _smoke_character(state_engine, scenario, world_bible, living_profile_factory)
    state.setdefault("world", {})["bible"] = world_bible
    state.setdefault("characters", {})["slot_1"] = character
    state.setdefault("meta", {})["phase"] = "active"
    state["meta"]["turn"] = 0
    state["meta"]["intro_state"] = _generated_intro_state()
    state_engine.normalize_campaign(campaign)
    campaign["state"]["meta"]["phase"] = "active"
    campaign["state"]["meta"]["intro_state"] = _generated_intro_state()
    state_engine.save_campaign(campaign, reason="ai_story_smoke_created")
    return campaign, Path(state_engine.CAMPAIGNS_DIR) / f"{campaign_id}.json"


def _smoke_player(hash_secret: Any, now: str) -> dict[str, Any]:
    return {
        "display_name": "AI Smoke Host",
        "player_token_hash": hash_secret("AI-SMOKE-TOKEN"),
        "joined_at": now,
        "last_seen_at": now,
    }


def _fill_setup(campaign: dict[str, Any], scenario: SmokeScenario) -> None:
    campaign["setup"]["world"]["completed"] = True
    campaign["setup"]["world"]["answers"] = dict(scenario.setup_answers)
    campaign["setup"]["world"]["summary"] = dict(scenario.setup_answers)
    campaign["setup"]["characters"]["slot_1"] = {
        "completed": True,
        "question_queue": [],
        "answers": dict(scenario.character),
        "summary": dict(scenario.character),
        "raw_transcript": [],
        "question_runtime": {},
    }


def _smoke_character(state_engine: Any, scenario: SmokeScenario, world_bible: dict[str, Any], living_profile_factory: Any) -> dict[str, Any]:
    character = state_engine.blank_character_state("slot_1")
    bio = character["bio"]
    bio["name"] = scenario.character["name"]
    bio["personality"] = list(scenario.character["personality"])
    bio["goal"] = scenario.character["goal"]
    bio["strength"] = scenario.character["strength"]
    bio["weakness"] = scenario.character["weakness"]
    bio["focus"] = scenario.character["focus"]
    character["class_current"] = state_engine.default_class_current()
    character["class_current"]["name"] = scenario.character["class_name"]
    character["skills"] = {
        "skill_smoke_primary": {
            "id": "skill_smoke_primary",
            "name": scenario.character["skill_name"],
            "description": "Smoke-Test Startfaehigkeit aus Charakterfokus und World Bible.",
        }
    }
    character["living_profile"] = living_profile_factory(character, world_bible=world_bible, setup_answers=scenario.character)
    return character


def _generated_intro_state() -> dict[str, str]:
    return {"status": "generated", "generated_turn_id": "turn_ai_smoke_seed", "last_error": ""}


if __name__ == "__main__":
    raise SystemExit(main())

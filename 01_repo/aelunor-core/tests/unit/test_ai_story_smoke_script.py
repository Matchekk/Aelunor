import json

from scripts import run_ai_story_smoke as smoke


def test_scenario_presets_exist():
    assert "dark-fantasy" in smoke.SCENARIOS
    assert "superhero-academy" in smoke.SCENARIOS
    assert smoke.SCENARIOS["dark-fantasy"].actions
    assert smoke.SCENARIOS["superhero-academy"].setup_answers["theme"]


def test_parse_args_and_turn_cap():
    args = smoke.parse_args(["--scenario", "superhero-academy", "--turns", "99", "--out", "tmp.md", "--keep-campaign"])

    assert args.scenario == "superhero-academy"
    assert args.out == "tmp.md"
    assert args.keep_campaign is True
    assert smoke.normalize_turn_count(args.turns) == smoke.MAX_TURNS


def test_resolve_provider_prefers_argument_then_aelunor_env():
    args = smoke.parse_args(["--provider", "ollama"])
    assert smoke.resolve_provider(args, {"AELUNOR_LLM_PROVIDER": "anthropic"}) == "ollama"

    args = smoke.parse_args([])
    assert smoke.resolve_provider(args, {"AELUNOR_LLM_PROVIDER": "anthropic"}) == "anthropic"


def test_missing_anthropic_key_returns_clean_error():
    ok, message = smoke.validate_provider_ready("anthropic", {})

    assert ok is False
    assert "ANTHROPIC_API_KEY" in message
    assert "sk-ant" not in message


def test_non_anthropic_provider_does_not_require_anthropic_key():
    ok, message = smoke.validate_provider_ready("ollama", {})

    assert ok is True
    assert message == ""


def test_render_smoke_report_contains_required_sections_and_no_secret(monkeypatch):
    secret = "sk-ant-test-secret"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    markdown = smoke.render_smoke_report(
        {
            "provider": "anthropic",
            "model": "claude-test",
            "scenario": "dark-fantasy",
            "campaign_id": "camp_1",
            "turns_requested": 3,
            "turns_completed": 2,
            "world_bible_quality_markdown": "# World Bible Quality Report\nsecret " + secret,
            "entity_guard_markdown": "# Entity Guard Review",
            "prompt_context_check": {
                "world_bible_summary": True,
                "living_profile_summary": True,
                "style_guard": True,
            },
            "sample_generated_names": ["Veyrhal"],
            "potential_problems": [],
            "turn_samples": [
                {
                    "player_action": "Ich pruefe die Runen.",
                    "gm_output_excerpt": "Die Runen antworten.",
                    "entity_guard_findings": ["merged: item 'Heiltrank' -> forbidden"],
                }
            ],
        }
    )

    assert "# AI Story Smoke Report" in markdown
    assert "Provider: anthropic" in markdown
    assert "Scenario: dark-fantasy" in markdown
    assert "## World Bible Quality" in markdown
    assert "## Entity Guard Summary" in markdown
    assert "World Bible Summary injected: yes" in markdown
    assert secret not in markdown
    assert "[redacted]" in markdown


def test_report_data_shape_is_json_serializable():
    data = {
        "provider": "anthropic",
        "model": "claude-test",
        "scenario": "superhero-academy",
        "campaign_id": "camp_2",
        "turns_requested": 1,
        "turns_completed": 1,
        "world_bible_quality_markdown": "quality",
        "entity_guard_markdown": "guard",
        "prompt_context_check": {"world_bible_summary": False, "living_profile_summary": False, "style_guard": False},
        "sample_generated_names": [],
        "potential_problems": ["Prompt Context Injection unvollstaendig."],
        "turn_samples": [],
    }

    json.dumps(data, ensure_ascii=False)
    markdown = smoke.render_smoke_report(data)

    assert "Potential Problems" in markdown
    assert "Prompt Context Injection unvollstaendig." in markdown

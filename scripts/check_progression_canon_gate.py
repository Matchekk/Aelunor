import copy
import importlib
import os
import sys
from typing import Any, Dict


def load_main() -> Any:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module("backend.main")


def fixture(main_module: Any) -> Dict[str, Any]:
    campaign = {
        "state": copy.deepcopy(main_module.INITIAL_STATE),
        "players": {},
        "claims": {},
        "setup": {
            "world": {"completed": True},
            "characters": {"slot_1": {"completed": True}},
        },
        "turns": [],
    }
    slot = "slot_1"
    state_before = copy.deepcopy(campaign["state"])
    state_before.setdefault("characters", {})
    state_before["characters"][slot] = main_module.blank_character_state(slot)
    state_before["characters"][slot]["bio"]["name"] = "Matchek"
    state_before.setdefault("meta", {})
    state_before["meta"]["turn"] = 4
    state_after = copy.deepcopy(state_before)
    campaign["state"] = state_after
    return {"campaign": campaign, "state_before": state_before, "state_after": state_after, "slot": slot}


def main() -> int:
    m = load_main()
    original_extractor = m.call_progression_canon_extractor
    slot = "slot_1"

    try:
        # 1) High confidence -> commit
        data = fixture(m)

        def extractor_high(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {
                "character_patch": {
                    "progression_events": [
                        {
                            "type": "skill_manifestation",
                            "actor": slot,
                            "severity": "high",
                            "reason": "Erstmanifestation",
                            "skill": {"name": "Dornenimpuls", "rank": "F", "description": "Manifestiert"},
                        }
                    ]
                },
                "confidence": "high",
                "confidence_score": 0.91,
                "model_confidence": "high",
                "heuristic_score": 0.86,
                "coverage": ["manifestation_claim", "skill_claim"],
                "reason": "klar",
            }

        m.call_progression_canon_extractor = extractor_high
        result = m.run_canon_gate(
            data["campaign"],
            state_before=data["state_before"],
            state_after=data["state_after"],
            patch=m.blank_patch(),
            actor=slot,
            action_type="do",
            player_text="Ich entfessle eine neue Kraft.",
            story_text="Matchek manifestiert erstmals eine Dornenkraft und reißt den Gegner zurück.",
            trace_ctx=None,
        )
        actor_patch = ((result.get("patch") or {}).get("characters") or {}).get(slot) or {}
        assert (result.get("meta") or {}).get("decision") == "committed", result
        assert actor_patch.get("progression_events"), "High-confidence Commit hat kein progression_event erzeugt."

        # 2) Medium confidence -> commit + flagged
        data = fixture(m)

        def extractor_medium(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {
                "character_patch": {"skills_delta": {"skill_windklinge": {"xp": 12}}},
                "confidence": "medium",
                "confidence_score": 0.61,
                "model_confidence": "medium",
                "heuristic_score": 0.54,
                "coverage": ["skill_level_claim"],
                "reason": "moderat",
            }

        m.call_progression_canon_extractor = extractor_medium
        result = m.run_canon_gate(
            data["campaign"],
            state_before=data["state_before"],
            state_after=data["state_after"],
            patch=m.blank_patch(),
            actor=slot,
            action_type="story",
            player_text="Ich verbessere meine Technik.",
            story_text="Matchek verbessert seine Technik deutlich und die Skillstufe steigt.",
            trace_ctx=None,
        )
        assert (result.get("meta") or {}).get("decision") == "flagged", result
        assert bool((result.get("meta") or {}).get("needs_review")), result

        # 3) Low confidence -> no commit
        data = fixture(m)

        def extractor_low(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {
                "character_patch": {"skills_set": {"skill_test": {"name": "Testskill", "rank": "F", "level": 1, "level_max": 10, "tags": [], "description": "x"}}},
                "confidence": "low",
                "confidence_score": 0.34,
                "model_confidence": "low",
                "heuristic_score": 0.3,
                "coverage": [],
                "reason": "unsicher",
            }

        m.call_progression_canon_extractor = extractor_low
        result = m.run_canon_gate(
            data["campaign"],
            state_before=data["state_before"],
            state_after=data["state_after"],
            patch=m.blank_patch(),
            actor=slot,
            action_type="do",
            player_text="Ich lerne vielleicht etwas.",
            story_text="Matchek könnte eventuell etwas lernen.",
            trace_ctx=None,
        )
        actor_patch = ((result.get("patch") or {}).get("characters") or {}).get(slot) or {}
        assert (result.get("meta") or {}).get("decision") == "skipped", result
        assert not actor_patch, "Low-confidence Pfad darf nichts committen."

        # 4) Narrator structured hat Vorrang -> extractor wird nicht gerufen
        data = fixture(m)
        calls = {"count": 0}

        def extractor_counter(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            calls["count"] += 1
            return extractor_high()

        m.call_progression_canon_extractor = extractor_counter
        patch = m.blank_patch()
        patch["characters"][slot] = {
            "skills_set": {
                "skill_schattenhieb": {
                    "id": "skill_schattenhieb",
                    "name": "Schattenhieb",
                    "rank": "F",
                    "level": 1,
                    "level_max": 10,
                    "tags": ["manifestation"],
                    "description": "Bereits strukturiert",
                }
            }
        }
        result = m.run_canon_gate(
            data["campaign"],
            state_before=data["state_before"],
            state_after=data["state_after"],
            patch=patch,
            actor=slot,
            action_type="do",
            player_text="Ich lerne einen Skill.",
            story_text="Matchek lernt einen Skill.",
            trace_ctx=None,
        )
        assert calls["count"] == 0, "Extractor wurde trotz bestehender strukturierter Progression aufgerufen."
        assert (result.get("meta") or {}).get("reason_code") == "STRUCTURED_ALREADY_PRESENT", result

        # 5) Soft-fail bei Extractor-Fehler
        data = fixture(m)

        def extractor_raise(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            raise RuntimeError("simulierter extractor-fehler")

        m.call_progression_canon_extractor = extractor_raise
        result = m.run_canon_gate(
            data["campaign"],
            state_before=data["state_before"],
            state_after=data["state_after"],
            patch=m.blank_patch(),
            actor=slot,
            action_type="do",
            player_text="Ich manifestiere etwas.",
            story_text="Matchek manifestiert erstmals eine neue Kraft.",
            trace_ctx=None,
        )
        assert (result.get("meta") or {}).get("decision") == "skipped", result
        assert (result.get("meta") or {}).get("reason_code") == "PROGRESSION_EXTRACTOR_ERROR", result

        print("OK: progression canon gate checks passed")
        return 0
    finally:
        m.call_progression_canon_extractor = original_extractor


if __name__ == "__main__":
    raise SystemExit(main())

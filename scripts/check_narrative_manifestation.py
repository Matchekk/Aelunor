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


def fresh_state(main_module: Any) -> Dict[str, Any]:
    state = copy.deepcopy(main_module.INITIAL_STATE)
    slot = "slot_1"
    state["characters"][slot] = main_module.blank_character_state(slot)
    state["characters"][slot]["bio"]["name"] = "Matchek"
    state["meta"]["turn"] = 1
    return state


def run_progression(
    main_module: Any,
    *,
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    story_text: str,
) -> Dict[str, Any]:
    campaign = {"state": state_after}
    return main_module.apply_progression_events(
        campaign,
        state_before,
        state_after,
        patch,
        actor=actor,
        action_type=action_type,
        player_text=player_text,
        story_text=story_text,
    )


def has_skill(state: Dict[str, Any], slot: str, skill_name_norm: str, main_module: Any) -> bool:
    skills = ((state.get("characters") or {}).get(slot) or {}).get("skills") or {}
    wanted = main_module.normalized_eval_text(skill_name_norm)
    for _, payload in skills.items():
        if not isinstance(payload, dict):
            continue
        if main_module.normalized_eval_text(payload.get("name", "")) == wanted:
            return True
    return False


def main() -> int:
    m = load_main()
    slot = "slot_1"

    # 1) Starke Erstmanifestation -> Skill entsteht (+ optional Seed)
    before = fresh_state(m)
    after = copy.deepcopy(before)
    after["meta"]["turn"] = 2
    strong_story = (
        "Matchek manifestiert erstmals eine wuchernde Myzelkraft. "
        "Wurzeln brechen aus dem Boden, fesseln den Gegner und kontrollieren das Kampffeld. "
        "Die Kultisten weichen erschrocken zurück, doch die Pilzvergiftung belastet seine Lebensenergie."
    )
    result = run_progression(
        m,
        state_before=before,
        state_after=after,
        patch=m.blank_patch(),
        actor=slot,
        action_type="do",
        player_text="Ich nutze in der Not die Kraft der Pilze.",
        story_text=strong_story,
    )
    assert has_skill(after, slot, "Myzelgriff", m), "Starke Manifestation hat keinen Skill erzeugt."
    seeds = ((after.get("characters") or {}).get(slot) or {}).get("class_path_seeds") or []
    assert isinstance(seeds, list), "class_path_seeds fehlt oder ist kein Array."
    assert result.get("events"), "Keine Progression-Events erzeugt."

    # 2) Vage Kraftnutzung -> kein neuer Skill
    before = fresh_state(m)
    after = copy.deepcopy(before)
    after["meta"]["turn"] = 3
    vague_story = "Matchek spürt Energie in sich und fokussiert sich. Die Lage bleibt angespannt."
    run_progression(
        m,
        state_before=before,
        state_after=after,
        patch=m.blank_patch(),
        actor=slot,
        action_type="story",
        player_text="Ich konzentriere mich.",
        story_text=vague_story,
    )
    assert not ((after.get("characters") or {}).get(slot) or {}).get("skills"), "Vage Szene hat unberechtigt Skill erzeugt."

    # 3) Explizite Manifestation im Patch -> keine serverseitige Duplikation
    before = fresh_state(m)
    after = copy.deepcopy(before)
    after["meta"]["turn"] = 4
    explicit_patch = m.blank_patch()
    explicit_patch["characters"].setdefault(slot, {})
    explicit_patch["characters"][slot]["progression_events"] = [
        {
            "type": "skill_manifestation",
            "actor": slot,
            "severity": "medium",
            "reason": "Expliziter Patch",
            "skill": {"name": "Myzelgriff", "rank": "F", "description": "Explizit manifestiert."},
        }
    ]
    result = run_progression(
        m,
        state_before=before,
        state_after=after,
        patch=explicit_patch,
        actor=slot,
        action_type="do",
        player_text="Ich manifestiere eine Technik.",
        story_text=strong_story,
    )
    manifests = [e for e in (result.get("events") or []) if str(e.get("type") or "") == "skill_manifestation"]
    assert len(manifests) == 1, "Explizite Manifestation wurde dupliziert."

    # 4) Wiederholte Nutzung -> kein neuer Skill-Klon
    before = fresh_state(m)
    before["characters"][slot]["skills"]["skill_myzelgriff"] = m.normalize_dynamic_skill_state(
        {"id": "skill_myzelgriff", "name": "Myzelgriff", "rank": "F", "level": 1},
        resource_name="Aether",
    )
    after = copy.deepcopy(before)
    after["meta"]["turn"] = 5
    run_progression(
        m,
        state_before=before,
        state_after=after,
        patch=m.blank_patch(),
        actor=slot,
        action_type="do",
        player_text="Ich nutze erneut Myzelgriff.",
        story_text="Matchek nutzt Myzelgriff erneut und drängt den Gegner zurück.",
    )
    assert len(((after.get("characters") or {}).get(slot) or {}).get("skills") or {}) == 1, "Wiederholte Nutzung hat Skill dupliziert."

    # 5) class_start_mode story + keine Klasse: Skill ja, Klasse nein (bei starker Manifestation)
    before = fresh_state(m)
    after = copy.deepcopy(before)
    after["meta"]["turn"] = 6
    run_progression(
        m,
        state_before=before,
        state_after=after,
        patch=m.blank_patch(),
        actor=slot,
        action_type="story",
        player_text="In der Not nutze ich die Pilzkraft.",
        story_text=strong_story,
    )
    assert ((after.get("characters") or {}).get(slot) or {}).get("class_current") is None, "Es wurde ungewollt direkt eine Klasse vergeben."
    assert ((after.get("characters") or {}).get(slot) or {}).get("skills"), "Skill fehlt trotz starker Manifestation ohne Klasse."

    print("OK: narrative manifestation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

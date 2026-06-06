from app.services.world.time import apply_world_time_advance, normalize_world_time


def test_normalize_world_time_current_minimal_payload_defaults_to_day_one_night() -> None:
    assert normalize_world_time({}) == {"day": 1, "month": 1, "year": 1, "time_of_day": "night", "weather": "", "absolute_day": 1}


def test_normalize_world_time_current_absolute_day_derives_calendar_fields() -> None:
    assert normalize_world_time({"world_time": {"absolute_day": 361}}) == {
        "absolute_day": 361,
        "year": 2,
        "month": 1,
        "day": 1,
        "time_of_day": "night",
        "weather": "",
    }


def test_normalize_world_time_current_negative_or_missing_values_are_clamped_and_defaulted() -> None:
    assert normalize_world_time({"world_time": {"absolute_day": -5, "day": -2, "time_of_day": "", "weather": None}}) == {
        "absolute_day": 1,
        "day": 1,
        "time_of_day": "night",
        "weather": "",
        "year": 1,
        "month": 1,
    }


def test_apply_world_time_advance_currently_updates_meta_world_time_and_compat_world_fields() -> None:
    state = {"meta": {"world_time": {"absolute_day": 30, "time_of_day": "morning", "weather": "Nebel"}}, "world": {"day": 0, "time": "", "weather": ""}}

    apply_world_time_advance(state, 2, "evening")

    assert state["meta"]["world_time"]["absolute_day"] == 32
    assert state["meta"]["world_time"]["month"] == 2
    assert state["meta"]["world_time"]["day"] == 2
    assert state["meta"]["world_time"]["time_of_day"] == "evening"
    assert state["world"] == {"day": 2, "time": "evening", "weather": "Nebel"}


def test_apply_world_time_advance_currently_preserves_existing_weather_and_defaults_missing_world() -> None:
    state = {"meta": {"world_time": {"absolute_day": 1, "weather": "Regen"}}}

    apply_world_time_advance(state, 0)

    assert state["meta"]["world_time"]["weather"] == "Regen"
    assert state["world"]["day"] == 1
    assert state["world"]["time"] == "night"
    assert state["world"]["weather"] == "Regen"

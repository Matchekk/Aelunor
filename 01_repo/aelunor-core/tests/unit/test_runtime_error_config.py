import unittest

from app import main
from app.config import errors as error_config
from app.config import runtime as runtime_config
from app.services import state_engine
from app.services import turn_engine


class RuntimeErrorConfigWiringTests(unittest.TestCase):
    def test_main_reexports_runtime_config_names(self) -> None:
        names = (
            "LEGACY_CHARACTERS",
            "ACTION_TYPES",
            "PHASES",
            "MAX_PLAYERS",
            "MAX_TURN_MODEL_ATTEMPTS",
            "CONTINUE_STORY_MARKER",
            "CAMPAIGN_LENGTHS",
            "TARGET_TURNS_DEFAULTS",
            "PACING_PROFILE_DEFAULTS",
            "TIMING_DEFAULTS",
            "TIMING_EMA_ALPHA",
            "AI_LATENCY_CLAMP",
            "PLAYER_LATENCY_CLAMP",
            "MIN_STORY_REWRITE_ATTEMPTS",
            "MAX_STORY_COMPRESS_ATTEMPTS",
            "EXTRACTION_QUARANTINE_DEFAULT_MAX",
            "EXTRACTION_REASON_GENERIC_LOCATION",
            "EXTRACTION_REASON_MISSING_ACQUIRE",
            "EXTRACTION_REASON_ENV_OBJECT",
            "EXTRACTION_REASON_VERB_STYLE_SKILL",
            "EXTRACTION_REASON_AMBIGUOUS_CLASS",
            "EXTRACTION_REASON_DUPLICATE",
            "EXTRACTION_REASON_LOW_CONFIDENCE",
            "EXTRACTION_REASON_CONFLICT_WITH_LLM",
        )

        for name in names:
            self.assertIs(getattr(main, name), getattr(runtime_config, name), name)

    def test_main_reexports_error_config_names(self) -> None:
        names = (
            "ERROR_CODE_NARRATOR_RESPONSE",
            "ERROR_CODE_JSON_REPAIR",
            "ERROR_CODE_SCHEMA_VALIDATION",
            "ERROR_CODE_PATCH_SANITIZE",
            "ERROR_CODE_PATCH_APPLY",
            "ERROR_CODE_EXTRACTOR",
            "ERROR_CODE_NORMALIZE",
            "ERROR_CODE_PERSISTENCE",
            "ERROR_CODE_SSE_BROADCAST",
            "ERROR_CODE_TURN_INTERNAL",
            "TURN_ERROR_USER_MESSAGES",
        )

        for name in names:
            self.assertIs(getattr(main, name), getattr(error_config, name), name)

    def test_configured_engines_keep_runtime_and_error_globals_available(self) -> None:
        for name in (
            "ACTION_TYPES",
            "PHASES",
            "MAX_PLAYERS",
            "TARGET_TURNS_DEFAULTS",
            "PACING_PROFILE_DEFAULTS",
            "TIMING_DEFAULTS",
            "AI_LATENCY_CLAMP",
            "PLAYER_LATENCY_CLAMP",
            "EXTRACTION_QUARANTINE_DEFAULT_MAX",
            "ERROR_CODE_NORMALIZE",
            "ERROR_CODE_PERSISTENCE",
            "ERROR_CODE_SSE_BROADCAST",
        ):
            self.assertIs(getattr(state_engine, name), getattr(main, name), name)

        for name in (
            "MAX_TURN_MODEL_ATTEMPTS",
            "MIN_STORY_REWRITE_ATTEMPTS",
            "MAX_STORY_COMPRESS_ATTEMPTS",
            "ERROR_CODE_NARRATOR_RESPONSE",
            "ERROR_CODE_JSON_REPAIR",
            "ERROR_CODE_PATCH_APPLY",
            "TURN_ERROR_USER_MESSAGES",
        ):
            self.assertIs(getattr(turn_engine, name), getattr(main, name), name)

    def test_runtime_values_and_error_fallbacks_keep_current_behavior(self) -> None:
        self.assertEqual(main.MAX_TURN_MODEL_ATTEMPTS, 3)
        self.assertEqual(main.TIMING_DEFAULTS["ai_latency_ema_sec"], 40.0)
        self.assertEqual(main.AI_LATENCY_CLAMP, (10.0, 90.0))
        self.assertEqual(turn_engine.user_message_for_error_code("missing"), main.TURN_ERROR_USER_MESSAGES[main.ERROR_CODE_TURN_INTERNAL])
        self.assertEqual(
            turn_engine.user_message_for_error_code(main.ERROR_CODE_JSON_REPAIR),
            "Die KI-Antwort war unvollständig oder ungültig formatiert.",
        )


if __name__ == "__main__":
    unittest.main()

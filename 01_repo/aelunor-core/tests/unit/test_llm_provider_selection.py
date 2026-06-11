import unittest

from app.adapters import llm_config
from app.adapters.anthropic_adapter import AnthropicAdapter, AnthropicSettings, FallbackLLMAdapter
from app.adapters.llm import OllamaAdapter


class _BoomPrimary:
    """Stub local adapter that always fails, simulating Ollama being unreachable."""

    def __init__(self) -> None:
        self.calls = 0

    def chat(self, system, user, **kwargs):
        self.calls += 1
        raise ConnectionError("ollama unreachable")

    def request_seed(self):
        return 42

    def status_payload(self):
        return {"provider": "ollama", "ollama_ok": False}


class _StubCloud:
    def __init__(self) -> None:
        self.calls = []

    def chat(self, system, user, **kwargs):
        self.calls.append((system, user, kwargs))
        return '{"story": "ok"}'

    def request_seed(self):
        return None

    def status_payload(self):
        return {"provider": "anthropic", "api_key_present": True}


class LLMProviderSelectionTests(unittest.TestCase):
    def test_explicit_providers_select_expected_adapter(self) -> None:
        self.assertIsInstance(llm_config.select_llm_adapter("ollama"), OllamaAdapter)
        self.assertIsInstance(llm_config.select_llm_adapter("anthropic"), AnthropicAdapter)

    def test_auto_stays_local_even_when_anthropic_key_exists(self) -> None:
        adapter = llm_config.select_llm_adapter("auto")
        self.assertIsInstance(adapter, OllamaAdapter)

    def test_fallback_routes_to_cloud_when_local_fails(self) -> None:
        primary, cloud = _BoomPrimary(), _StubCloud()
        adapter = FallbackLLMAdapter(primary, cloud)
        result = adapter.chat("system", "user", format_schema={"type": "object"}, timeout=90)
        self.assertEqual(result, '{"story": "ok"}')
        self.assertEqual(primary.calls, 1)
        self.assertEqual(len(cloud.calls), 1)
        # The fallback forwards the original kwargs to the cloud adapter unchanged.
        self.assertEqual(cloud.calls[0][2]["timeout"], 90)

    def test_fallback_prefers_local_when_available(self) -> None:
        class _OkPrimary(_StubCloud):
            def chat(self, system, user, **kwargs):
                return "local-result"

        cloud = _StubCloud()
        adapter = FallbackLLMAdapter(_OkPrimary(), cloud)
        self.assertEqual(adapter.chat("s", "u"), "local-result")
        self.assertEqual(cloud.calls, [])  # cloud never touched when local works

    def test_fallback_request_seed_delegates_to_primary(self) -> None:
        adapter = FallbackLLMAdapter(_BoomPrimary(), _StubCloud())
        self.assertEqual(adapter.request_seed(), 42)

    def test_anthropic_adapter_interface(self) -> None:
        adapter = AnthropicAdapter(AnthropicSettings(model="claude-opus-4-8", max_tokens=8192, timeout_sec=240))
        self.assertIsNone(adapter.request_seed())  # Claude API has no seed
        status = adapter.status_payload()
        self.assertEqual(status["provider"], "anthropic")
        self.assertEqual(status["configured_model"], "claude-opus-4-8")
        self.assertIn("api_key_present", status)


if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from requests import ConnectionError

from app.adapters.llm import OllamaAdapter, OllamaSettings
from app.routers.llm import build_llm_router


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ConnectionError(f"status {self.status_code}")


def _client():
    app = FastAPI()
    app.include_router(build_llm_router())
    return TestClient(app)


class LlmModelCatalogRouterTests(unittest.TestCase):
    def test_models_endpoint_returns_normalized_models(self):
        client = _client()
        with patch("app.services.llm.model_catalog.requests.get") as get:
            get.return_value = _Response(
                {
                    "models": [
                        {
                            "name": "llama3.1:8b",
                            "modified_at": "2026-06-12T10:00:00Z",
                            "size": 123,
                            "details": {"family": "llama", "parameter_size": "8B"},
                        }
                    ]
                }
            )
            response = client.get("/api/llm/models?ollamaBaseUrl=http://127.0.0.1:11434")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["status"], "connected")
        self.assertEqual(body["models"][0]["name"], "llama3.1:8b")
        self.assertEqual(body["models"][0]["family"], "llama")

    def test_models_endpoint_reports_offline_without_stacktrace(self):
        client = _client()
        with patch("app.services.llm.model_catalog.requests.get", side_effect=ConnectionError("offline")):
            response = client.get("/api/llm/models?ollamaBaseUrl=http://127.0.0.1:11434")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["status"], "offline")
        self.assertEqual(body["models"], [])
        self.assertIn("Ollama ist nicht erreichbar", body["message"])

    def test_models_endpoint_uses_default_url_for_blank_input(self):
        client = _client()
        with patch("app.services.llm.model_catalog.requests.get") as get:
            get.return_value = _Response({"models": []})
            response = client.get("/api/llm/models?ollamaBaseUrl=%20")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(get.call_args.args[0], "http://127.0.0.1:11434/api/tags")

    def test_test_endpoint_uses_short_chat_probe(self):
        client = _client()
        with patch("app.services.llm.model_catalog.requests.post") as post:
            post.return_value = _Response({"message": {"content": "bereit"}})
            response = client.post(
                "/api/llm/test",
                json={"ollamaBaseUrl": "http://127.0.0.1:11434", "model": "llama3.1:8b"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "llama3.1:8b")
        self.assertEqual(payload["options"]["num_ctx"], 512)


def _adapter(model: str = "gemma4:12b") -> OllamaAdapter:
    return OllamaAdapter(
        OllamaSettings(
            url="http://127.0.0.1:11434",
            model=model,
            timeout_sec=30,
            seed=None,
            temperature=0.6,
            num_ctx=8192,
            repeat_penalty=1.18,
            repeat_last_n=192,
        )
    )


class LlmActiveModelRouterTests(unittest.TestCase):
    def test_set_model_switches_adapter_and_persists(self):
        client = _client()
        adapter = _adapter()
        with tempfile.TemporaryDirectory() as tmp, patch(
            "app.adapters.ollama_config.OLLAMA_ADAPTER", adapter
        ), patch("app.services.llm.active_model.DATA_DIR", tmp):
            response = client.put("/api/llm/model", json={"model": "gemma4:e4b"})

            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertTrue(body["ok"])
            self.assertEqual(body["model"], "gemma4:e4b")
            self.assertEqual(adapter.settings.model, "gemma4:e4b")
            with open(os.path.join(tmp, "llm_settings.json"), encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["model"], "gemma4:e4b")

            current = client.get("/api/llm/model").json()
            self.assertTrue(current["ok"])
            self.assertEqual(current["model"], "gemma4:e4b")

    def test_set_model_rejects_blank_without_side_effects(self):
        client = _client()
        adapter = _adapter()
        with tempfile.TemporaryDirectory() as tmp, patch(
            "app.adapters.ollama_config.OLLAMA_ADAPTER", adapter
        ), patch("app.services.llm.active_model.DATA_DIR", tmp):
            response = client.put("/api/llm/model", json={"model": "  "})

            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertFalse(body["ok"])
            self.assertEqual(body["model"], "gemma4:12b")
            self.assertEqual(adapter.settings.model, "gemma4:12b")
            self.assertFalse(os.path.exists(os.path.join(tmp, "llm_settings.json")))


if __name__ == "__main__":
    unittest.main()

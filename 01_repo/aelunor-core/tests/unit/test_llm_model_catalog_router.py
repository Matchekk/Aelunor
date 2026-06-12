import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from requests import ConnectionError

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


if __name__ == "__main__":
    unittest.main()

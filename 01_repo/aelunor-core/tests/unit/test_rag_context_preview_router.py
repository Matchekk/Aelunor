import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.context import build_context_router
from app.schemas.api import ContextQueryIn, RagContextPreviewIn
from app.services.rag import RagContextPreviewDependencies


def _fake_state():
    return {
        "npcs": [
            {
                "id": "npc-aria",
                "name": "Aria Sturmgeboren",
                "role": "Wächterin",
                "description": "Verteidigt das Tor von Thalûn.",
            }
        ],
        "quests": [
            {
                "id": "q-crown",
                "title": "Finde die Krone",
                "status": "open",
                "goal": "Die Krone aus den Sümpfen bergen.",
            }
        ],
    }


class _Recorder:
    def __init__(self, *, raise_on_auth=False):
        self.raise_on_auth = raise_on_auth
        self.auth_calls = []
        self.load_calls = []

    def load_campaign(self, campaign_id):
        self.load_calls.append(campaign_id)
        return {"id": campaign_id, "state": _fake_state()}

    def authenticate_player(self, campaign, player_id, player_token, required=False):
        self.auth_calls.append((player_id, player_token, required))
        if self.raise_on_auth:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="auth required")


def _client(recorder):
    app = FastAPI()
    app.include_router(
        build_context_router(
            context_query_model=ContextQueryIn,
            context_service_dependencies=lambda: None,
            rag_context_preview_model=RagContextPreviewIn,
            rag_context_preview_dependencies=lambda: RagContextPreviewDependencies(
                load_campaign=recorder.load_campaign,
                authenticate_player=recorder.authenticate_player,
            ),
        )
    )
    return TestClient(app)


class RagPreviewRouterTests(unittest.TestCase):
    def test_post_returns_200_with_preview(self):
        recorder = _Recorder()
        client = _client(recorder)
        response = client.post(
            "/api/campaigns/camp-1/context/rag-preview",
            json={"text": "Aria Krone", "max_results": 3},
            headers={"X-Player-Id": "p-1", "X-Player-Token": "tok"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["campaign_id"], "camp-1")
        self.assertIn("index", body)
        self.assertIn("results", body)
        self.assertIn("context", body)
        self.assertIn("warnings", body)
        self.assertTrue(body["results"])
        # Router stays thin: headers reach the service as required auth.
        self.assertEqual(recorder.auth_calls, [("p-1", "tok", True)])
        self.assertEqual(recorder.load_calls, ["camp-1"])

    def test_invalid_auth_propagates_error(self):
        recorder = _Recorder(raise_on_auth=True)
        client = _client(recorder)
        response = client.post(
            "/api/campaigns/camp-1/context/rag-preview",
            json={"text": "Aria"},
        )
        self.assertEqual(response.status_code, 403)

    def test_source_types_and_max_chars_forwarded_to_service(self):
        recorder = _Recorder()
        client = _client(recorder)
        response = client.post(
            "/api/campaigns/camp-1/context/rag-preview",
            json={
                "text": "Krone Sümpfe",
                "source_types": ["quest"],
                "max_chars": 700,
            },
            headers={"X-Player-Id": "p-1", "X-Player-Token": "tok"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["query"]["source_types"], ["quest"])
        self.assertEqual(body["query"]["max_chars"], 700)
        self.assertTrue(all(r["source_type"] == "quest" for r in body["results"]))
        self.assertLessEqual(len(body["context"]), 700)


if __name__ == "__main__":
    unittest.main()

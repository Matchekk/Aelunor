from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse

import pytest
import requests
from fastapi.testclient import TestClient


LOCAL_LLM_ENV = "AELUNOR_RUN_LOCAL_LLM_SMOKE"
OLLAMA_MODEL = "gemma4:12b"
OLLAMA_URL = "http://127.0.0.1:11434"
SLOT_ID = "slot_1"

PLAYER_ACTIONS = [
    "Ich untersuche die auffälligste Spur oder das seltsamste Objekt in der Szene und achte auf Gefahr.",
    "Ich spreche die wichtigste anwesende Figur direkt an und versuche herauszufinden, was sie wirklich will.",
    "Ich treffe eine riskante Entscheidung: Ich verlasse die sichere Position und folge dem gefährlichsten Hinweis.",
]

ACTION_RESPONSE_MARKERS = [
    ("spur", "objekt", "gefahr", "untersuch", "prüf", "zeichen", "find", "entdeck", "auffällig", "seltsam"),
    ("sprech", "frag", "antwort", "figur", "will", "absicht", "motiv", "blick", "stimme", "wahr"),
    ("risk", "verlässt", "verlasse", "sicher", "position", "gefährlich", "hinweis", "folg", "entscheidung", "pfad"),
]

CONCRETE_SCENE_MARKERS = (
    "ort", "szene", "licht", "schatten", "spur", "tor", "dorf", "wald", "ruine", "pfad", "figur", "stimme",
    "abtei", "zöllner", "aschencirkel", "bestie", "kult", "gefahr", "ziel", "konflikt", "boden", "materie",
    "fragment", "rune", "gestalt", "energie", "relikt", "barriere", "artefakt", "wesen",
)

GENERIC_FALLBACK_FRAGMENTS = (
    "die szene wird fortgesetzt", "die lage entwickelt sich konsistent weiter", "setzt die handlung fort",
    "tritt in die erste szene dieser chronik", "ein konkreter nächster schritt liegt vor der gruppe",
)


def install_no_external_requests_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    original_request = requests.sessions.Session.request
    allowed_hosts = {"127.0.0.1", "localhost", "::1"}

    def guarded_request(session: requests.sessions.Session, method: str, url: str, *args: Any, **kwargs: Any) -> requests.Response:
        host = urlparse(str(url)).hostname
        if host not in allowed_hosts:
            raise AssertionError(f"Externer Netzwerkaufruf verboten: {method} {url}")
        return original_request(session, method, url, *args, **kwargs)

    monkeypatch.setattr(requests.sessions.Session, "request", guarded_request)


def require_local_ollama_model() -> None:
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=15)
        response.raise_for_status()
    except Exception as exc:
        pytest.fail(
            f"Lokales Ollama ist unter {OLLAMA_URL} nicht erreichbar: {exc}. "
            f"Starte Ollama lokal und prüfe mit `ollama list`, ob {OLLAMA_MODEL} installiert ist."
        )
    models = (response.json() or {}).get("models") or []
    names = {str(entry.get("name") or entry.get("model") or "") for entry in models if isinstance(entry, dict)}
    if OLLAMA_MODEL not in names:
        available = ", ".join(sorted(name for name in names if name)) or "<keine>"
        pytest.fail(
            f"Ollama-Modell {OLLAMA_MODEL!r} wurde nicht gefunden. Verfügbare Modelle: {available}. "
            "Bitte mit `ollama list` prüfen. Der Test wechselt nicht auf ein anderes Modell."
        )


def reload_app_modules_for_local_env() -> None:
    for name in sorted((name for name in sys.modules if name == "app" or name.startswith("app.")), key=len, reverse=True):
        sys.modules.pop(name, None)


def create_campaign(client: TestClient) -> Dict[str, Any]:
    payload = post_ok(client, "/api/campaigns", json={"title": "Local Gemma Live Campaign", "display_name": "Local Host"})
    assert payload["campaign_id"]
    assert payload["join_code"]
    assert payload["player_id"]
    assert payload["player_token"]
    return payload


def post_ok(client: TestClient, path: str, **kwargs: Any) -> Dict[str, Any]:
    response = client.post(path, **kwargs)
    assert response.status_code == 200, response.text
    return response.json()


def get_ok(client: TestClient, path: str, **kwargs: Any) -> Dict[str, Any]:
    response = client.get(path, **kwargs)
    assert response.status_code == 200, response.text
    return response.json()


def preview_answers(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    answers = []
    for entry in payload.get("preview_answers", []):
        answer = dict(entry.get("answer") or {})
        answer["question_id"] = entry["question_id"]
        answers.append(answer)
    assert answers
    return answers


def replace_answer(answers: List[Dict[str, Any]], question_id: str, **updates: Any) -> None:
    for answer in answers:
        if answer.get("question_id") == question_id:
            answer.update(updates)
            return
    raise AssertionError(f"Preview-Antwort {question_id!r} fehlt.")


def latest_narration(campaign: Dict[str, Any]) -> str:
    active_turns = campaign.get("active_turns") or []
    assert active_turns
    return str(active_turns[-1].get("gm_text_display") or "").strip()


def assert_campaign_state_valid(campaign: Dict[str, Any], *, player_id: str, expected_turn: int) -> None:
    json.dumps(campaign, ensure_ascii=False)
    state = campaign.get("state") or {}
    meta = state.get("meta") or {}
    assert meta.get("phase") == "active"
    assert meta.get("turn") == expected_turn
    assert campaign.get("claims", {}).get(SLOT_ID) == player_id
    assert SLOT_ID in (state.get("characters") or {})
    assert campaign.get("active_turns")
    assert (meta.get("intro_state") or {}).get("status") == "generated"


def assert_playable_narration(text: str, *, label: str) -> None:
    normalized = normalize(text)
    assert len(text.strip()) >= 120, f"{label} ist zu kurz oder leer: {text!r}"
    assert len(text.strip()) <= 3200, f"{label} ist zu lang für eine spielbare Turn-Narration: {len(text)} Zeichen"
    assert not any(fragment in normalized for fragment in GENERIC_FALLBACK_FRAGMENTS), f"{label} wirkt wie generischer Fallback: {text!r}"
    leak_markers = ('"patch"', '\\"patch\\"', '"requests"', '\\"requests\\"', "output-kontrakt", "player_action", "context_packet")
    assert not any(marker in normalized for marker in leak_markers), f"{label} enthält JSON-/Prompt-Leaks: {text!r}"
    commentary_markers = ("i will now", "let me re-read", "okay, let's go", "the prompt asks me", "the core issue is", "anmerkung:", "update für dich")
    assert not any(marker in normalized for marker in commentary_markers), f"{label} enthält Modell-Selbstkommentar: {text!r}"
    assert "\n---" not in text, f"{label} enthält Markdown-Trenner: {text!r}"
    assert not re.search(r"(?:_[a-z0-9]){16,}", text, flags=re.IGNORECASE), f"{label} enthält beschädigte Tokenketten: {text!r}"
    marker_hits = [marker for marker in CONCRETE_SCENE_MARKERS if marker in normalized]
    assert len(marker_hits) >= 2, f"{label} enthält zu wenig konkrete Szene/Ansatz-Marker: {text!r}"


def assert_response_reacts_to_action(text: str, *, index: int) -> None:
    markers = ACTION_RESPONSE_MARKERS[index - 1]
    assert any(marker in normalize(text) for marker in markers), (
        f"Turn {index} reagiert nicht erkennbar auf die Spieleraktion. "
        f"Erwartete Marker aus {markers}, Antwort war: {text!r}"
    )


def assert_distinct_turn_narrations(narrations: Iterable[str]) -> None:
    values = list(narrations)
    assert len(values) == 3
    assert len(set(values)) == 3, "Die drei Turn-Narrationen sind exakt gleich."
    first_sentences = [first_sentence(value) for value in values]
    assert len(set(first_sentences)) > 1, "Alle drei Turn-Narrationen beginnen mit identischem ersten Satz."
    for left_index, left in enumerate(values):
        for right_index, right in enumerate(values[left_index + 1 :], start=left_index + 2):
            ratio = SequenceMatcher(None, normalize(left), normalize(right)).ratio()
            assert ratio < 0.86, f"Turn {left_index + 1} und Turn {right_index} sind zu ähnlich: ratio={ratio:.3f}"


def first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    return normalize(parts[0] if parts else text)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def compact(text: str, limit: int = 420) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("ISEKAI_BASE_URL", "http://localhost:8080").rstrip("/")
DOCKER_COMPOSE_FILE = ROOT / "docker-compose.yml"
DEFAULT_MODELS = ["gemma3:12b", "gemma3:8b"]
STARTUP_TIMEOUT_SECONDS = 180


class BenchmarkError(RuntimeError):
    pass


def run_command(args: List[str], *, env: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        args,
        cwd=ROOT,
        env=merged_env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def ensure_model(model: str) -> None:
    print(f"[pull] {model}")
    result = run_command(["ollama", "pull", model], timeout=60 * 60)
    if result.returncode != 0:
        raise BenchmarkError(f"Could not pull {model}:\n{result.stderr or result.stdout}")


def restart_app(model: str) -> None:
    print(f"[compose] restart with {model}")
    env = {"OLLAMA_MODEL": model}
    down = run_command(["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "down"], env=env, timeout=5 * 60)
    if down.returncode != 0:
        raise BenchmarkError(f"docker compose down failed for {model}:\n{down.stderr or down.stdout}")
    up = run_command(["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "up", "-d", "--build"], env=env, timeout=30 * 60)
    if up.returncode != 0:
        raise BenchmarkError(f"docker compose up failed for {model}:\n{up.stderr or up.stdout}")


def wait_for_app(model: str) -> Dict[str, Any]:
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    last_error = ""
    while time.time() < deadline:
        try:
            response = requests.get(f"{BASE_URL}/api/llm/status", timeout=10)
            response.raise_for_status()
            payload = response.json()
            if payload.get("configured_model") == model:
                return payload
            last_error = f"configured model is {payload.get('configured_model')!r}, expected {model!r}"
        except Exception as exc:  # pragma: no cover - operational polling
            last_error = str(exc)
        time.sleep(2)
    raise BenchmarkError(f"App did not become ready for {model}: {last_error}")


def api(method: str, path: str, *, headers: Optional[Dict[str, str]] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers=headers,
        json=body,
        timeout=240,
    )
    response.raise_for_status()
    if not response.text.strip():
        return {}
    return response.json()


def viewer_headers(player_id: str, player_token: str) -> Dict[str, str]:
    return {
        "X-Player-Id": player_id,
        "X-Player-Token": player_token,
    }


def mutate_preview_answers(preview_answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mutated: List[Dict[str, Any]] = []
    for entry in preview_answers:
        answer = dict(entry["answer"])
        if entry["question_id"] == "player_count":
            answer["value"] = "1"
            answer["selected"] = "1"
            answer["other_text"] = ""
        mutated.append(answer)
    return mutated


def first_slot_id(campaign: Dict[str, Any]) -> str:
    slots = campaign.get("available_slots") or []
    if not slots:
        raise BenchmarkError("Campaign returned no available slots.")
    return slots[0]["slot_id"]


def run_single_benchmark(model: str) -> Dict[str, Any]:
    ensure_model(model)
    restart_app(model)
    llm_status = wait_for_app(model)

    timings: Dict[str, float] = {}

    start = time.perf_counter()
    created = api(
        "POST",
        "/api/campaigns",
        body={"title": f"Benchmark {model}", "display_name": "Host"},
    )
    timings["create_campaign_seconds"] = round(time.perf_counter() - start, 2)

    campaign_id = created["campaign_id"]
    player_id = created["player_id"]
    player_token = created["player_token"]
    headers = viewer_headers(player_id, player_token)

    start = time.perf_counter()
    world_preview = api(
        "POST",
        f"/api/campaigns/{campaign_id}/setup/world/random",
        headers=headers,
        body={"mode": "all", "preview_answers": []},
    )
    timings["world_preview_seconds"] = round(time.perf_counter() - start, 2)

    preview_answers = mutate_preview_answers(world_preview["preview_answers"])

    start = time.perf_counter()
    world_apply = api(
        "POST",
        f"/api/campaigns/{campaign_id}/setup/world/random/apply",
        headers=headers,
        body={"mode": "all", "preview_answers": preview_answers},
    )
    timings["world_apply_seconds"] = round(time.perf_counter() - start, 2)

    slot_id = first_slot_id(world_apply["campaign"])

    start = time.perf_counter()
    claimed = api(
        "POST",
        f"/api/campaigns/{campaign_id}/slots/{slot_id}/claim",
        headers=headers,
    )
    timings["claim_slot_seconds"] = round(time.perf_counter() - start, 2)

    start = time.perf_counter()
    char_preview = api(
        "POST",
        f"/api/campaigns/{campaign_id}/slots/{slot_id}/setup/random",
        headers=headers,
        body={"mode": "all", "preview_answers": []},
    )
    timings["character_preview_seconds"] = round(time.perf_counter() - start, 2)

    start = time.perf_counter()
    char_apply = api(
        "POST",
        f"/api/campaigns/{campaign_id}/slots/{slot_id}/setup/random/apply",
        headers=headers,
        body={"mode": "all", "preview_answers": [entry["answer"] for entry in char_preview["preview_answers"]]},
    )
    timings["character_apply_seconds"] = round(time.perf_counter() - start, 2)

    campaign = char_apply["campaign"]
    phase = campaign.get("state", {}).get("meta", {}).get("phase")
    active_turns = campaign.get("active_turns") or []
    if phase != "adventure":
        raise BenchmarkError(f"{model} did not reach adventure phase. Current phase: {phase}")
    if not active_turns:
        raise BenchmarkError(f"{model} did not generate an intro turn.")

    intro_turn = active_turns[-1]

    start = time.perf_counter()
    turn_result = api(
        "POST",
        f"/api/campaigns/{campaign_id}/turns",
        headers=headers,
        body={
            "actor": slot_id,
            "action_type": "do",
            "content": "Ich sichere zuerst den Bereich, pruefe Spuren am Boden und suche einen gefahrlosen Weg fuer den naechsten Schritt.",
        },
    )
    timings["story_turn_seconds"] = round(time.perf_counter() - start, 2)

    final_campaign = turn_result["campaign"]
    latest_turn = (final_campaign.get("active_turns") or [])[-1]

    return {
        "model": model,
        "llm_status": llm_status,
        "campaign_id": campaign_id,
        "slot_id": slot_id,
        "timings": timings,
        "world_randomized_count": world_preview.get("randomized_count"),
        "character_randomized_count": char_preview.get("randomized_count"),
        "intro_turn_length": len((intro_turn.get("gm_text_display") or "").strip()),
        "story_turn_length": len((latest_turn.get("gm_text_display") or "").strip()),
        "story_request_count": len(latest_turn.get("requests") or []),
        "story_excerpt": (latest_turn.get("gm_text_display") or "")[:500],
    }


def main() -> int:
    models = sys.argv[1:] or DEFAULT_MODELS
    results = []
    for model in models:
        print(f"[benchmark] {model}")
        started_at = time.perf_counter()
        result = run_single_benchmark(model)
        result["total_seconds"] = round(time.perf_counter() - started_at, 2)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n[summary]")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

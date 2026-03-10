import json
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

LIVE_ACTIVITY_TTLS = {
    "typing_turn": 5,
    "editing_turn": 6,
    "claiming_slot": 6,
    "building_character": 8,
    "building_world": 8,
    "reviewing_choices": 6,
}
BLOCKING_ACTION_TTL = 120
SSE_PING_INTERVAL = 15

LIVE_STATE_LOCK = threading.Lock()
LIVE_STATE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_live_state() -> Dict[str, Any]:
    return {
        "activities": {},
        "blocking_action": None,
        "version": 0,
        "subscribers": [],
    }


def iso_to_epoch(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def live_state_for_campaign(campaign_id: str) -> Dict[str, Any]:
    with LIVE_STATE_LOCK:
        return live_state_for_campaign_unlocked(campaign_id)


def live_state_for_campaign_unlocked(campaign_id: str) -> Dict[str, Any]:
    state = LIVE_STATE_REGISTRY.get(campaign_id)
    if state is None:
        state = default_live_state()
        LIVE_STATE_REGISTRY[campaign_id] = state
    return state


def live_presence_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    activities: Dict[str, Dict[str, Any]] = {}
    for player_id, activity in (state.get("activities") or {}).items():
        activities[player_id] = {
            key: value
            for key, value in activity.items()
            if not str(key).startswith("_")
        }
    blocking = state.get("blocking_action")
    return {
        "version": state.get("version", 0),
        "activities": activities,
        "blocking_action": {
            key: value
            for key, value in (blocking or {}).items()
            if not str(key).startswith("_")
        }
        if blocking
        else None,
    }


def cleanup_live_state_locked(state: Dict[str, Any]) -> bool:
    changed = False
    now = time.time()
    expired_players = [
        player_id
        for player_id, activity in (state.get("activities") or {}).items()
        if float(activity.get("_expires_at_ts") or 0) <= now
    ]
    for player_id in expired_players:
        state["activities"].pop(player_id, None)
        changed = True
    blocking = state.get("blocking_action")
    if blocking and float(blocking.get("_expires_at_ts") or 0) <= now:
        state["blocking_action"] = None
        changed = True
    if changed:
        state["version"] = int(state.get("version", 0)) + 1
    return changed


def cleanup_live_state(campaign_id: str) -> bool:
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        return cleanup_live_state_locked(state)


def live_snapshot(campaign_id: str) -> Dict[str, Any]:
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        return live_presence_snapshot(state)


def broadcast_live_event(campaign_id: str, event_name: str, payload: Dict[str, Any]) -> None:
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        subscribers = list(state.get("subscribers") or [])
    message = {"event": event_name, "data": payload}
    stale: List[queue.Queue] = []
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(message)
        except queue.Full:
            stale.append(subscriber)
    if not stale:
        return
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        state["subscribers"] = [subscriber for subscriber in state.get("subscribers") or [] if subscriber not in stale]


def broadcast_presence_sync(campaign_id: str) -> None:
    snapshot = live_snapshot(campaign_id)
    broadcast_live_event(campaign_id, "presence_sync", snapshot)


def broadcast_campaign_sync(campaign_id: str, reason: str = "campaign_updated") -> None:
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        state["version"] = int(state.get("version", 0)) + 1
        version = state["version"]
    broadcast_live_event(
        campaign_id,
        "campaign_sync",
        {
            "version": version,
            "reason": reason,
        },
    )


def make_activity_label(campaign: Dict[str, Any], player_id: str, kind: str) -> str:
    display_name = (campaign.get("players", {}).get(player_id, {}) or {}).get("display_name") or "Jemand"
    return {
        "typing_turn": f"{display_name} schreibt...",
        "editing_turn": f"{display_name} ändert die Geschichte...",
        "claiming_slot": f"{display_name} wählt einen Platz in der Gruppe...",
        "building_character": f"{display_name} formt die Figur...",
        "building_world": f"{display_name} entwirft die Welt...",
        "reviewing_choices": f"{display_name} prüft die nächsten Schritte...",
    }.get(kind, f"{display_name} ist aktiv...")


def make_blocking_label(campaign: Dict[str, Any], player_id: Optional[str], kind: str) -> str:
    display_name = (campaign.get("players", {}).get(player_id or "", {}) or {}).get("display_name") or "Jemand"
    return {
        "generate_intro": f"{display_name} beschwört den Auftakt der Geschichte...",
        "submit_turn": f"{display_name} handelt in der Szene...",
        "continue_turn": f"{display_name} führt die Geschichte weiter...",
        "retry_turn": f"{display_name} formt den letzten Moment neu...",
        "undo_turn": f"{display_name} nimmt den letzten Schritt zurück...",
        "character_randomize": f"{display_name} ruft eine neue Gestalt hervor...",
        "world_randomize": f"{display_name} lässt die Welt Gestalt annehmen...",
        "building_character": f"{display_name} formt die Figur...",
        "building_world": f"{display_name} entwirft die Welt...",
    }.get(kind, f"{display_name} wirkt auf die Szene ein...")


def set_live_activity(
    campaign: Dict[str, Any],
    player_id: str,
    kind: str,
    *,
    slot_id: Optional[str] = None,
    target_turn_id: Optional[str] = None,
) -> Dict[str, Any]:
    ttl = LIVE_ACTIVITY_TTLS.get(kind, 6)
    now = utc_now()
    expires_at_ts = time.time() + ttl
    activity = {
        "kind": kind,
        "label": make_activity_label(campaign, player_id, kind),
        "slot_id": slot_id,
        "target_turn_id": target_turn_id,
        "blocking": False,
        "updated_at": now,
        "expires_at": datetime.fromtimestamp(expires_at_ts, tz=timezone.utc).isoformat(),
        "_expires_at_ts": expires_at_ts,
    }
    campaign_id = campaign["campaign_meta"]["campaign_id"]
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        state["activities"][player_id] = activity
        state["version"] = int(state.get("version", 0)) + 1
    broadcast_presence_sync(campaign_id)
    return activity


def clear_live_activity(campaign_id: str, player_id: Optional[str]) -> None:
    if not player_id:
        return
    changed = False
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        if player_id in state.get("activities", {}):
            state["activities"].pop(player_id, None)
            state["version"] = int(state.get("version", 0)) + 1
            changed = True
    if changed:
        broadcast_presence_sync(campaign_id)


def start_blocking_action(
    campaign: Dict[str, Any],
    *,
    player_id: Optional[str],
    kind: str,
    slot_id: Optional[str] = None,
) -> Dict[str, Any]:
    now = utc_now()
    expires_at_ts = time.time() + BLOCKING_ACTION_TTL
    blocking_action = {
        "player_id": player_id,
        "slot_id": slot_id,
        "kind": kind,
        "label": make_blocking_label(campaign, player_id, kind),
        "started_at": now,
        "_expires_at_ts": expires_at_ts,
    }
    campaign_id = campaign["campaign_meta"]["campaign_id"]
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        state["blocking_action"] = blocking_action
        state["version"] = int(state.get("version", 0)) + 1
    broadcast_presence_sync(campaign_id)
    return blocking_action


def clear_blocking_action(campaign_id: str) -> None:
    changed = False
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        if state.get("blocking_action"):
            state["blocking_action"] = None
            state["version"] = int(state.get("version", 0)) + 1
            changed = True
    if changed:
        broadcast_presence_sync(campaign_id)


def sse_message(event_name: str, payload: Dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def campaign_event_stream(campaign_id: str) -> Generator[str, None, None]:
    subscriber: queue.Queue = queue.Queue(maxsize=100)
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        state["subscribers"].append(subscriber)
    yield sse_message("presence_sync", live_snapshot(campaign_id))
    idle_ticks = 0
    try:
        while True:
            try:
                message = subscriber.get(timeout=1.0)
                idle_ticks = 0
                yield sse_message(message["event"], message["data"])
            except queue.Empty:
                idle_ticks += 1
                if cleanup_live_state(campaign_id):
                    yield sse_message("presence_sync", live_snapshot(campaign_id))
                    idle_ticks = 0
                    continue
                if idle_ticks >= SSE_PING_INTERVAL:
                    idle_ticks = 0
                    yield sse_message("ping", {"ts": utc_now()})
    finally:
        with LIVE_STATE_LOCK:
            state = live_state_for_campaign_unlocked(campaign_id)
            state["subscribers"] = [entry for entry in state.get("subscribers") or [] if entry is not subscriber]


def clear_campaign_state(campaign_id: str) -> None:
    with LIVE_STATE_LOCK:
        LIVE_STATE_REGISTRY.pop(campaign_id, None)

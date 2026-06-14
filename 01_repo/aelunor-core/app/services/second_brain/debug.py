"""Read-only debug overview for the Second Brain (developer endpoint).

Exposes only aggregate counts and meta — never node text, prompts, embeddings
or secrets. Campaign-scoped and safe: flag off -> enabled False, no brain ->
exists False, never raises, never 500s.
"""

from __future__ import annotations

import logging

from app.config.feature_flags import second_brain_enabled

from .locator import is_safe_campaign_id, open_campaign_brain

_log = logging.getLogger("aelunor.second_brain")

_ENTITY_KINDS = ("npc", "location", "item", "character", "faction", "concept")


def _empty_counts() -> dict:
    return {
        "event": 0,
        "fact": 0,
        "entity": 0,
        "edge": 0,
        "open_thread": 0,
        "memory_card": 0,
        "by_kind": {},
    }


def brain_overview(campaign_id: str, *, campaigns_dir: str | None = None) -> dict:
    """Aggregate, secret-free overview of one campaign's brain."""
    overview = {
        "campaign_id": campaign_id,
        "enabled": second_brain_enabled(),
        "exists": False,
        "counts": _empty_counts(),
        "last_processed_turn": None,
        "schema_version": None,
        "failed_jobs": 0,
        "warnings": [],
    }
    if not is_safe_campaign_id(campaign_id):
        overview["warnings"].append("invalid campaign_id")
        return overview
    try:
        brain = open_campaign_brain(campaign_id, campaigns_dir=campaigns_dir, create=False)
    except Exception as exc:  # noqa: BLE001 - debug must never 500
        overview["warnings"].append(f"open_failed: {type(exc).__name__}")
        return overview
    if brain is None:
        return overview
    try:
        overview["exists"] = True
        raw = brain.store.counts(campaign_id)
        overview["counts"] = {
            "event": int(raw.get("event", 0)),
            "fact": int(raw.get("fact", 0)),
            "entity": sum(int(raw.get(k, 0)) for k in _ENTITY_KINDS),
            "edge": int(raw.get("edges", 0)),
            "open_thread": int(raw.get("open_thread", 0)),
            "memory_card": int(raw.get("event", 0)),
            "by_kind": {k: int(v) for k, v in raw.items() if k != "edges"},
        }
        overview["last_processed_turn"] = brain.store.get_meta("last_processed_turn_number")
        overview["schema_version"] = brain.store.schema_version
        failed = brain.store.get_meta("failed_jobs")
        overview["failed_jobs"] = int(failed) if (failed or "").isdigit() else 0
        last_failure = brain.store.get_meta("last_failure")
        if last_failure:
            overview["warnings"].append(last_failure)
    except Exception as exc:  # noqa: BLE001
        overview["warnings"].append(f"read_failed: {type(exc).__name__}")
    finally:
        try:
            brain.store.close()
        except Exception:  # noqa: BLE001
            pass
    return overview

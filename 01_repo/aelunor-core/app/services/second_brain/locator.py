"""Per-campaign Second Brain location + safe open (persistence pillar).

Each campaign gets its own database file at
``CAMPAIGNS_DIR/<campaign_id>/brain/brain.sqlite`` — a sibling of the existing
single-file ``CAMPAIGNS_DIR/<campaign_id>.json``. There is never a shared or
global brain file, and the ``campaign_id`` column inside the DB is a second
guard against cross-campaign mixing.

``open_campaign_brain`` is the safe entry point: it never raises. A missing
campaign id, an unsafe path, or a corrupt/unopenable database returns ``None``
(logged) so a brain problem can never fail a turn.
"""

from __future__ import annotations

import logging
import os
import re

from .embeddings import EmbeddingPort
from .service import SecondBrain
from .store import SecondBrainStore

_log = logging.getLogger("aelunor.second_brain")

_BRAIN_DIRNAME = "brain"
_BRAIN_FILENAME = "brain.sqlite"
# Campaign ids look like ``camp_<hexslug>``; be strict to avoid path traversal.
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _campaigns_dir(campaigns_dir: str | None) -> str:
    if campaigns_dir:
        return campaigns_dir
    # Imported lazily so tests can pass an explicit dir without runtime config.
    from app.core.paths import CAMPAIGNS_DIR

    return CAMPAIGNS_DIR


def is_safe_campaign_id(campaign_id: str) -> bool:
    return (
        isinstance(campaign_id, str)
        and bool(campaign_id)
        and campaign_id not in (".", "..")
        and bool(_SAFE_ID_RE.match(campaign_id))
    )


def brain_dir_for_campaign(campaign_id: str, *, campaigns_dir: str | None = None) -> str:
    return os.path.join(_campaigns_dir(campaigns_dir), campaign_id, _BRAIN_DIRNAME)


def brain_path_for_campaign(campaign_id: str, *, campaigns_dir: str | None = None) -> str:
    return os.path.join(
        brain_dir_for_campaign(campaign_id, campaigns_dir=campaigns_dir),
        _BRAIN_FILENAME,
    )


def open_campaign_brain(
    campaign_id: str,
    *,
    campaigns_dir: str | None = None,
    create: bool = True,
    embedder: EmbeddingPort | None = None,
    wal: bool = False,
) -> SecondBrain | None:
    """Open (or create) a campaign's brain. Returns ``None`` on any problem,
    never raises — a brain failure must not break the turn."""
    if not is_safe_campaign_id(campaign_id):
        _log.warning("second_brain: refusing unsafe campaign_id %r", campaign_id)
        return None
    path = brain_path_for_campaign(campaign_id, campaigns_dir=campaigns_dir)
    try:
        if not create and not os.path.exists(path):
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        store = SecondBrainStore(path, wal=wal)
        return SecondBrain(store=store, embedder=embedder)
    except Exception as exc:  # noqa: BLE001 - brain must never break a turn
        _log.warning("second_brain: could not open brain for %s: %s", campaign_id, exc)
        return None

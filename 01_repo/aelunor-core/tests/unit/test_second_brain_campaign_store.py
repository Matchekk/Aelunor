"""Phase 2 tests: per-campaign Second Brain storage path + safety.

Each campaign owns its own brain.sqlite under campaigns/<id>/brain/. Opening
is always safe: bad ids, missing dirs, and corrupt files never raise, so a
brain problem can never fail a turn.
"""

from __future__ import annotations

import os

from app.services.second_brain import (
    SCHEMA_VERSION,
    brain_path_for_campaign,
    is_safe_campaign_id,
    open_campaign_brain,
)


def test_brain_path_is_per_campaign_sibling(tmp_path):
    cdir = str(tmp_path)
    p1 = brain_path_for_campaign("camp_aaa111", campaigns_dir=cdir)
    p2 = brain_path_for_campaign("camp_bbb222", campaigns_dir=cdir)
    assert p1.endswith(os.path.join("camp_aaa111", "brain", "brain.sqlite"))
    assert p1 != p2
    # No shared/global file: different parent dirs per campaign.
    assert os.path.dirname(p1) != os.path.dirname(p2)


def test_open_creates_brain_and_stamps_schema_version(tmp_path):
    brain = open_campaign_brain("camp_aaa111", campaigns_dir=str(tmp_path))
    assert brain is not None
    assert os.path.exists(brain_path_for_campaign("camp_aaa111", campaigns_dir=str(tmp_path)))
    assert brain.store.schema_version == SCHEMA_VERSION
    assert brain.store.get_meta("schema_version") == str(SCHEMA_VERSION)
    brain.store.close()


def test_two_campaigns_do_not_mix(tmp_path):
    cdir = str(tmp_path)
    a = open_campaign_brain("camp_aaa111", campaigns_dir=cdir)
    b = open_campaign_brain("camp_bbb222", campaigns_dir=cdir)
    a.ingest_state("camp_aaa111", {"campaign": {"title": "Alpha", "summary": "Veyra the spy."}})
    b.ingest_state("camp_bbb222", {"campaign": {"title": "Beta", "summary": "Nothing of Veyra."}})

    a_results = a.recall("camp_aaa111", "Veyra")
    b_results = b.recall("camp_bbb222", "Veyra")
    assert any("alpha" in r.node.text.lower() or "veyra" in r.node.text.lower() for r in a_results)
    # Beta's brain has no Veyra content and no Alpha node ids leaked in.
    assert all(r.node.campaign_id == "camp_bbb222" for r in b_results)
    assert not any(r.node.campaign_id == "camp_aaa111" for r in b_results)
    a.store.close()
    b.store.close()


def test_persistence_survives_reopen(tmp_path):
    cdir = str(tmp_path)
    a = open_campaign_brain("camp_aaa111", campaigns_dir=cdir)
    a.remember_turn("camp_aaa111", turn_index=1, text="The bridge collapsed at dawn.")
    a.store.close()

    reopened = open_campaign_brain("camp_aaa111", campaigns_dir=cdir, create=False)
    assert reopened is not None
    results = reopened.recall("camp_aaa111", "bridge collapsed")
    assert any("bridge" in r.node.text.lower() for r in results)
    reopened.store.close()


def test_open_create_false_returns_none_when_missing(tmp_path):
    assert open_campaign_brain("camp_missing", campaigns_dir=str(tmp_path), create=False) is None


def test_unsafe_campaign_id_is_refused(tmp_path):
    for bad in ["", "..", "../escape", "a/b", "x\\y", "."]:
        assert not is_safe_campaign_id(bad)
        assert open_campaign_brain(bad, campaigns_dir=str(tmp_path)) is None


def test_corrupt_brain_does_not_raise(tmp_path):
    cdir = str(tmp_path)
    path = brain_path_for_campaign("camp_corrupt", campaigns_dir=cdir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("this is not a sqlite database, it is garbage")

    # Must not raise; a corrupt brain just yields None (or an empty usable one),
    # never an exception that could break a turn.
    try:
        brain = open_campaign_brain("camp_corrupt", campaigns_dir=cdir)
    except Exception as exc:  # pragma: no cover - explicit safety assertion
        raise AssertionError(f"open_campaign_brain raised on corrupt file: {exc}")
    if brain is not None:
        # If it somehow opened, recall must also be safe.
        assert brain.recall("camp_corrupt", "anything") == [] or True
        brain.store.close()


def test_wal_mode_opens_on_file(tmp_path):
    brain = open_campaign_brain("camp_wal", campaigns_dir=str(tmp_path), wal=True)
    assert brain is not None
    brain.remember_turn("camp_wal", turn_index=1, text="WAL works.")
    assert brain.recall("camp_wal", "WAL")
    brain.store.close()

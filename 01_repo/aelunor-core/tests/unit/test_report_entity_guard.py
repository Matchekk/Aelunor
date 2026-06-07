import json
from pathlib import Path

from scripts import report_entity_guard as report


def _entry(name: str, entity_type: str, status: str, score: int, *, terms=None):
    return {
        "entity_type": entity_type,
        "name": name,
        "status": status,
        "score": score,
        "reasons": [f"{name} reason"],
        "forbidden_terms_found": list(terms or []),
        "avoid_terms_found": [],
        "matched_roots": [],
        "source_paths": ["patch.path"],
        "requires_review": status in {"generic", "forbidden", "needs_review", "unknown"},
    }


def _campaign_with_guard():
    return {
        "campaign_meta": {"campaign_id": "camp_1", "title": "Guarded"},
        "turns": [
            {
                "turn_id": "turn_1",
                "turn_number": 1,
                "entity_guard": {
                    "summary": {"total": 2},
                    "reports": [
                        _entry("Feuerball", "skill", "forbidden", 10, terms=["Feuerball"]),
                        _entry("Nok-Thar", "location", "ok", 90),
                    ],
                },
            },
            {
                "turn_id": "turn_2",
                "turn_number": 2,
                "entity_guard": {
                    "narrator": {"summary": {"total": 1}, "reports": [_entry("Heiltrank", "item", "generic", 25, terms=["Heiltrank"])]},
                    "extractor": {"summary": {"total": 1}, "reports": [_entry("Kriegerklasse", "class", "weak", 45)]},
                    "merged": {"summary": {"total": 1}, "reports": [_entry("Magiergilde", "faction", "forbidden", 5, terms=["Magiergilde"])]},
                },
            },
        ],
    }


def _campaign(campaign_id: str, title: str, turns: list[dict], *, bible: dict | None = None):
    return {
        "campaign_meta": {"campaign_id": campaign_id, "title": title, "created_at": "2026-06-07T12:00:00+00:00"},
        "state": {"world": {"bible": bible or {"identity": {"world_name": "Smoke World"}}}},
        "turns": turns,
    }


def _guard_turn(turn_number: int = 1, reports: list[dict] | None = None):
    return {
        "turn_id": f"turn_{turn_number}",
        "turn_number": turn_number,
        "entity_guard": {"summary": {"total": len(reports or [])}, "reports": reports or [_entry("Nok-Thar", "location", "ok", 90)]},
    }


def test_empty_campaign_does_not_crash():
    review = report.build_entity_guard_review([{"campaign_meta": {"campaign_id": "empty"}, "turns": []}])

    assert review["summary"]["campaigns_scanned"] == 1
    assert review["summary"]["turns_scanned"] == 0
    assert review["summary"]["entities_assessed"] == 0


def test_campaign_without_guard_data_has_zero_guarded_turns():
    review = report.build_entity_guard_review([{"campaign_meta": {"campaign_id": "old"}, "turns": [{"turn_number": 1}]}])

    assert review["summary"]["turns_scanned"] == 1
    assert review["summary"]["turns_with_guard_data"] == 0


def test_extract_entity_guard_reports_supports_flat_and_stage_shapes():
    turns = _campaign_with_guard()["turns"]

    assert len(report.extract_entity_guard_reports_from_turn(turns[0])) == 1
    assert len(report.extract_entity_guard_reports_from_turn(turns[1])) == 3


def test_flatten_contains_campaign_id_and_turn_number():
    campaign = _campaign_with_guard()
    flat = report.flatten_entity_guard_report(
        campaign["turns"][0]["entity_guard"],
        campaign_meta=campaign["campaign_meta"],
        turn=campaign["turns"][0],
    )

    assert flat[0]["campaign_id"] == "camp_1"
    assert flat[0]["turn_number"] == 1
    assert flat[0]["name"] == "Feuerball"


def test_build_review_counts_status_distribution_and_entity_types():
    review = report.build_entity_guard_review([_campaign_with_guard()])

    assert review["summary"]["turns_scanned"] == 2
    assert review["summary"]["turns_with_guard_data"] == 2
    assert review["summary"]["entities_assessed"] == 5
    assert review["summary"]["status_distribution"]["forbidden"] == 2
    assert review["by_entity_type"]["skill"]["forbidden"] == 1
    assert review["by_entity_type"]["location"]["ok"] == 1


def test_build_review_dedupes_identical_entity_guard_reports():
    duplicate = _entry("Nok-Thar", "location", "weak", 45)
    campaign = _campaign("camp_dup", "AI Smoke - Duplicate", [_guard_turn(reports=[duplicate, duplicate, duplicate])])

    review = report.build_entity_guard_review([campaign])

    assert review["summary"]["entities_assessed"] == 1
    assert len(review["worst_reports"]) == 1
    assert review["worst_reports"][0]["count"] == 3


def test_problem_names_and_worst_reports_are_aggregated_and_sorted():
    review = report.build_entity_guard_review([_campaign_with_guard()])

    assert review["problem_names"][0]["name"] in {"Magiergilde", "Feuerball", "Heiltrank"}
    assert review["worst_reports"][0]["name"] == "Magiergilde"
    assert review["worst_reports"][0]["score"] == 5


def test_problem_terms_are_aggregated():
    review = report.build_entity_guard_review([_campaign_with_guard()])
    terms = {row["term"]: row["count"] for row in review["problem_terms"]}

    assert terms["Feuerball"] == 1
    assert terms["Heiltrank"] == 1
    assert terms["Magiergilde"] == 1


def test_render_markdown_contains_required_sections():
    markdown = report.render_markdown_report(report.build_entity_guard_review([_campaign_with_guard()]), limit=5)

    assert "# Entity Guard Review" in markdown
    assert "## Status Distribution" in markdown
    assert "## Worst Reports" in markdown
    assert "Feuerball" in markdown


def test_render_markdown_shows_active_filters():
    review = report.build_entity_guard_review(
        [_campaign("camp_smoke", "AI Smoke - Clean", [_guard_turn()])],
        filter_meta={"filters": {"only_smoke": True, "exclude_empty": True, "min_turns": 1}, "campaigns_skipped": 2},
    )
    markdown = report.render_markdown_report(review)

    assert "Filters:" in markdown
    assert "- only_smoke: true" in markdown
    assert "- exclude_empty: true" in markdown
    assert "- min_turns: 1" in markdown
    assert "Campaigns skipped: 2" in markdown


def test_json_review_is_serializable():
    review = report.build_entity_guard_review([_campaign_with_guard()])

    encoded = json.dumps(review, ensure_ascii=False)

    assert "Guarded" in encoded


def test_load_campaign_json_and_iter_campaign_files_use_temp_data(tmp_path, monkeypatch):
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    path = campaigns_dir / "camp_1.json"
    path.write_text(json.dumps(_campaign_with_guard(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(report, "CAMPAIGNS_DIR", str(campaigns_dir))

    assert report.iter_campaign_files("camp_1") == [path]
    assert report.load_campaign_json(path)["campaign_meta"]["campaign_id"] == "camp_1"
    assert report.load_campaign_json(campaigns_dir / "missing.json") is None


def test_main_filters_exclude_empty_only_smoke_and_min_turns(tmp_path, monkeypatch):
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    campaigns = [
        _campaign("smoke_ok", "AI Smoke - Clean", [_guard_turn()]),
        _campaign("smoke_old", "AI Smoke - Clean", [_guard_turn()]),
        _campaign("smoke_empty", "AI Smoke - Empty", []),
        _campaign("pipeline", "Pipeline Campaign", [_guard_turn()]),
    ]
    campaigns[1]["campaign_meta"]["created_at"] = "2026-06-01T12:00:00+00:00"
    for campaign in campaigns:
        (campaigns_dir / f"{campaign['campaign_meta']['campaign_id']}.json").write_text(json.dumps(campaign, ensure_ascii=False), encoding="utf-8")
    out_path = tmp_path / "report.json"
    monkeypatch.setattr(report, "CAMPAIGNS_DIR", str(campaigns_dir))
    monkeypatch.setattr(
        "sys.argv",
        ["report_entity_guard.py", "--only-smoke", "--exclude-empty", "--min-turns", "1", "--json", "--out", str(out_path)],
    )

    assert report.main() == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["summary"]["campaigns_scanned"] == 1
    assert payload["summary"]["campaigns_skipped"] == 3
    assert payload["summary"]["skip_reasons"]["older_smoke_run"] == 1
    assert payload["summary"]["filters"]["only_smoke"] is True
    assert payload["summary"]["filters"]["exclude_empty"] is True
    assert payload["summary"]["filters"]["min_turns"] == 1
    assert payload["campaigns"][0]["campaign_id"] == "smoke_ok"


def test_main_title_filters_work(tmp_path, monkeypatch):
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    for campaign in [
        _campaign("dark", "AI Smoke - Dark Fantasy", [_guard_turn()]),
        _campaign("super", "AI Smoke - Superhero Academy", [_guard_turn()]),
    ]:
        (campaigns_dir / f"{campaign['campaign_meta']['campaign_id']}.json").write_text(json.dumps(campaign, ensure_ascii=False), encoding="utf-8")
    out_path = tmp_path / "report.json"
    monkeypatch.setattr(report, "CAMPAIGNS_DIR", str(campaigns_dir))
    monkeypatch.setattr(
        "sys.argv",
        ["report_entity_guard.py", "--title-contains", "Smoke", "--exclude-title", "Superhero", "--json", "--out", str(out_path)],
    )

    assert report.main() == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["summary"]["campaigns_scanned"] == 1
    assert payload["campaigns"][0]["campaign_id"] == "dark"


def test_main_json_out_writes_only_explicit_out_file(tmp_path, monkeypatch):
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    (campaigns_dir / "camp_1.json").write_text(json.dumps(_campaign_with_guard(), ensure_ascii=False), encoding="utf-8")
    out_path = tmp_path / "report.json"
    monkeypatch.setattr(report, "CAMPAIGNS_DIR", str(campaigns_dir))
    monkeypatch.setattr(
        "sys.argv",
        ["report_entity_guard.py", "--campaign-id", "camp_1", "--json", "--out", str(out_path)],
    )

    assert report.main() == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["summary"]["campaigns_scanned"] == 1
    assert len(list(tmp_path.glob("*.json"))) == 1

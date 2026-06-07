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

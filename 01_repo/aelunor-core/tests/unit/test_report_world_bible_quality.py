import json

from scripts import report_world_bible_quality as report


def _full_bible():
    return {
        "created_from_setup": {"theme": "Dark Fantasy"},
        "identity": {
            "world_name": "Veyrhal",
            "core_pitch": "Eide haben Kosten.",
            "genre_shape": "Dark Fantasy",
            "dominant_mood": "sakral und kalt",
            "forbidden_generic_feel": ["Feuerball"],
        },
        "linguistics": {
            "world_languages": {
                "primary_language": {
                    "name": "Veyrisch",
                    "sound": "hart",
                    "common_roots": ["veyr", "karn", "nok", "thar", "orn"],
                    "example_words": {"oath": "karn"},
                }
            },
            "race_languages": {"race_lizard": {"common_roots": {"ssar": "warm"}}},
            "place_name_aliases": {"loc_1": {"common_name": "Karnfurt"}},
            "translation_rules": {"levels": {"weak": "Roots"}},
            "comprehension_rules": ["Teilwissen erzeugt Fehler."],
        },
        "naming_rules": {
            key: {"patterns": ["{root}-{concept}"], "examples": [f"{key}-Karn"], "avoid": ["Generic"]}
            for key in ("people", "settlements", "regions", "ruins", "factions", "skills", "items", "beasts", "titles")
        },
        "metaphysics": {
            "main_power_name": "Veyr",
            "main_power_description": "Eidkraft.",
            "power_source": "Eid und Blut",
            "power_limitations": ["Bricht bei Luege."],
            "world_laws": ["Eide brennen."],
            "taboos": ["Tote Namen."],
        },
        "progression": {
            "rank_language": {"F": "Funke"},
            "class_origin_rules": "Klassen aus Eid.",
            "class_naming_rules": ["Root + Rolle"],
            "skill_manifestation_rules": ["Kostenpflichtig"],
            "skill_cost_rules": ["Veyr kostet Erinnerung."],
        },
        "races_and_beasts": {
            "race_origin_rules": "alte Linien",
            "race_naming_rules": ["Endonyme"],
            "beast_origin_rules": "Oekologie",
            "beast_naming_rules": ["Spur + Warnung"],
            "ecology_rules": ["Habitat"],
        },
        "items": {
            "item_naming_rules": ["Material + Herkunft"],
            "rarity_language": {"rare": "Eidrar"},
            "material_vocabulary": ["Karnstahl", "Veyrglas", "Nokasche"],
            "relic_rules": ["Nebenwirkung"],
            "earth_item_transformation_rules": ["Umdeutung"],
        },
        "tone_and_style": {
            "narration_rules": ["koerperlich"],
            "forbidden_words": ["Power Strike"],
            "preferred_motifs": ["Asche"],
            "sensory_palette": {"sights": ["Risse"], "sounds": ["Ketten"], "smells": [], "textures": []},
        },
    }


def _campaign(campaign_id="camp_1", bible=None, *, title=None, turns=None, created_at="2026-06-07T12:00:00+00:00"):
    return {
        "campaign_meta": {"campaign_id": campaign_id, "title": title or campaign_id.title(), "created_at": created_at},
        "state": {"world": {"bible": bible or {}}},
        "turns": list(turns or []),
    }


def _turn(turn_number=1):
    return {"turn_id": f"turn_{turn_number}", "turn_number": turn_number}


def test_campaign_without_bible_does_not_crash_and_scores_low():
    quality = report.assess_world_bible_quality({}, campaign=_campaign())

    assert quality["score"] < 30
    assert "World Bible missing." in quality["warnings"]
    assert "state.world.bible" in quality["missing_blocks"]


def test_full_fantasy_bible_scores_high():
    quality = report.assess_world_bible_quality(_full_bible(), campaign=_campaign(bible=_full_bible()))

    assert quality["score"] >= 85
    assert quality["naming_mode"] == "dark_fantasy"


def test_thin_bible_has_weak_areas():
    bible = {"identity": {"world_name": "Thin"}}
    quality = report.assess_world_bible_quality(bible, campaign=_campaign(bible=bible))

    assert quality["score"] < 50
    assert "linguistics" in quality["weak_areas"]
    assert "naming_rules" in quality["weak_areas"]


def test_identity_scoring_counts_expected_fields():
    result = report.assess_identity_quality(_full_bible())

    assert result["score"] == 10
    assert result["max"] == 10


def test_linguistics_scoring_recognizes_roots_and_race_languages():
    result = report.assess_linguistics_quality(_full_bible(), campaign={"state": {"world": {"races": {"race_lizard": {}}}}})

    assert result["score"] >= 18
    assert not any("roots too few" in warning for warning in result["warnings"])


def test_naming_rules_scoring_recognizes_patterns_examples_and_avoids():
    result = report.assess_naming_rules_quality(_full_bible(), naming_mode="dark_fantasy")

    assert result["score"] == 20


def test_superhero_bible_is_not_penalized_for_modern_examples():
    bible = _full_bible()
    bible["identity"]["genre_shape"] = "Superhelden-Akademie modern_japanese"
    bible["naming_rules"]["people"]["examples"] = ["Akira Tanaka"]
    bible["naming_rules"]["factions"]["examples"] = ["Hoshino Academy"]
    bible["races_and_beasts"] = {}

    quality = report.assess_world_bible_quality(bible, campaign=_campaign(bible=bible))

    assert quality["naming_mode"] == "superhero_academy"
    assert quality["category_scores"]["races_and_beasts"]["score"] >= 7
    assert "superhero_academy mode lacks central naming examples" not in quality["warnings"]


def test_dark_fantasy_with_too_few_roots_warns():
    bible = _full_bible()
    bible["linguistics"]["world_languages"]["primary_language"]["common_roots"] = ["nok"]

    quality = report.assess_world_bible_quality(bible, campaign=_campaign(bible=bible))

    assert any("roots too few" in warning for warning in quality["warnings"])


def test_build_review_aggregates_multiple_campaigns():
    review = report.build_world_bible_quality_review([_campaign("good", _full_bible()), _campaign("empty", {})])

    assert review["summary"]["campaigns_scanned"] == 2
    assert review["summary"]["average_score"] is not None
    assert len(review["campaigns"]) == 2


def test_render_markdown_contains_breakdown_and_details():
    markdown = report.render_markdown_report(report.build_world_bible_quality_review([_campaign("good", _full_bible())]))

    assert "# World Bible Quality Report" in markdown
    assert "## Campaign Breakdown" in markdown
    assert "## Detailed Findings" in markdown
    assert "Category Scores:" in markdown


def test_render_markdown_shows_active_filters():
    review = report.build_world_bible_quality_review(
        [_campaign("smoke", _full_bible(), title="AI Smoke - Clean", turns=[_turn()])],
        filter_meta={"filters": {"only_smoke": True, "exclude_empty": True, "min_turns": 1}, "campaigns_skipped": 3},
    )
    markdown = report.render_markdown_report(review)

    assert "Filters:" in markdown
    assert "- only_smoke: true" in markdown
    assert "- exclude_empty: true" in markdown
    assert "- min_turns: 1" in markdown
    assert "Campaigns skipped: 3" in markdown


def test_json_review_is_serializable():
    encoded = json.dumps(report.build_world_bible_quality_review([_campaign("good", _full_bible())]), ensure_ascii=False)

    assert "good" in encoded


def test_campaign_file_helpers_and_main_out(tmp_path, monkeypatch):
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    (campaigns_dir / "camp_1.json").write_text(json.dumps(_campaign("camp_1", _full_bible()), ensure_ascii=False), encoding="utf-8")
    out_path = tmp_path / "quality.json"
    monkeypatch.setattr(report, "CAMPAIGNS_DIR", str(campaigns_dir))
    monkeypatch.setattr("sys.argv", ["report_world_bible_quality.py", "--campaign-id", "camp_1", "--json", "--out", str(out_path)])

    assert report.iter_campaign_files("camp_1") == [campaigns_dir / "camp_1.json"]
    assert report.load_campaign_json(campaigns_dir / "camp_1.json")["campaign_meta"]["campaign_id"] == "camp_1"
    assert report.main() == 0
    assert json.loads(out_path.read_text(encoding="utf-8"))["summary"]["campaigns_scanned"] == 1


def test_main_filters_exclude_empty_only_smoke_and_min_turns(tmp_path, monkeypatch):
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    campaigns = [
        _campaign("smoke_ok", _full_bible(), title="AI Smoke - Clean", turns=[_turn()]),
        _campaign("smoke_old", _full_bible(), title="AI Smoke - Clean", turns=[_turn()], created_at="2026-06-01T12:00:00+00:00"),
        _campaign("smoke_empty", _full_bible(), title="AI Smoke - Empty", turns=[]),
        _campaign("pipeline", {}, title="Pipeline Campaign", turns=[_turn()]),
    ]
    for campaign in campaigns:
        (campaigns_dir / f"{campaign['campaign_meta']['campaign_id']}.json").write_text(json.dumps(campaign, ensure_ascii=False), encoding="utf-8")
    out_path = tmp_path / "quality.json"
    monkeypatch.setattr(report, "CAMPAIGNS_DIR", str(campaigns_dir))
    monkeypatch.setattr(
        "sys.argv",
        ["report_world_bible_quality.py", "--only-smoke", "--exclude-empty", "--min-turns", "1", "--json", "--out", str(out_path)],
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


def test_main_title_and_created_after_filters_work(tmp_path, monkeypatch):
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    campaigns = [
        _campaign("dark", _full_bible(), title="AI Smoke - Dark Fantasy", turns=[_turn()], created_at="2026-06-07T12:00:00+00:00"),
        _campaign("super", _full_bible(), title="AI Smoke - Superhero Academy", turns=[_turn()], created_at="2026-06-07T12:00:00+00:00"),
        _campaign("old", _full_bible(), title="AI Smoke - Old", turns=[_turn()], created_at="2026-06-01T12:00:00+00:00"),
    ]
    for campaign in campaigns:
        (campaigns_dir / f"{campaign['campaign_meta']['campaign_id']}.json").write_text(json.dumps(campaign, ensure_ascii=False), encoding="utf-8")
    out_path = tmp_path / "quality.json"
    monkeypatch.setattr(report, "CAMPAIGNS_DIR", str(campaigns_dir))
    monkeypatch.setattr(
        "sys.argv",
        ["report_world_bible_quality.py", "--title-contains", "Smoke", "--exclude-title", "Superhero", "--created-after", "2026-06-06", "--json", "--out", str(out_path)],
    )

    assert report.main() == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["summary"]["campaigns_scanned"] == 1
    assert payload["campaigns"][0]["campaign_id"] == "dark"

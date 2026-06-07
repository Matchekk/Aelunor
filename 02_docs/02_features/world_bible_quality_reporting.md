# World Bible Quality Reporting

`scripts/report_world_bible_quality.py` bewertet read-only die Qualitaet der
persistierten World Bible pro Campaign. Das Script veraendert keine Campaigns
und ruft keine LLMs oder externen Services auf.

## Zweck

Entity Guard Reports sind nur dann aussagekraeftig, wenn die World Bible genug
Naming-DNA liefert. Der Quality Report hilft zu unterscheiden:

- Die KI ignoriert eine gute Bible.
- Die Bible ist zu duenn.
- Naming Rules passen nicht zum Genre.
- Roots, Examples, Race-Sprachen, Materialien oder Skill-Patterns fehlen.

## Beispielaufrufe

```powershell
python scripts/report_world_bible_quality.py
python scripts/report_world_bible_quality.py --campaign-id camp_123
python scripts/report_world_bible_quality.py --json
python scripts/report_world_bible_quality.py --out reports/world_bible_quality.md
python scripts/report_world_bible_quality.py --limit 50
```

## Kategorie-Scoring

Der Score liegt bei 0 bis 100:

- `identity`: 10 Punkte
- `linguistics`: 20 Punkte
- `naming_rules`: 20 Punkte
- `metaphysics`: 15 Punkte
- `progression`: 10 Punkte
- `races_and_beasts`: 10 Punkte
- `items`: 10 Punkte
- `tone_and_style`: 5 Punkte

Der Report zeigt Kategorie-Scores, Weak Areas, Warnings und Missing Blocks.

## Genre- und Naming-Mode

Das Script nutzt `infer_world_naming_mode(...)` aus dem Entity Guard. Eine
Superhelden-Akademie oder moderne Mystery-Welt wird nicht dafuer bestraft, dass
sie normale Namen oder Schul-/Hero-Begriffe nutzt. Eine Dark-Fantasy-Welt wird
dagegen staerker auf Roots, Sprachlogik und spezifische Examples geprueft.

## Nutzung mit Entity Guard Reporting

Nutze zuerst diesen Report, um die Bible-Qualitaet zu verstehen. Danach kann
`entity_guard_reporting.md` zeigen, welche Namen in Turns wirklich schwach,
generisch oder forbidden waren.

## Spaetere Schritte

Moegliche Folgearbeiten:

- bessere Bible-Erzeugung im Setup
- Soft Naming Retry
- Runtime Bible Extension
- Hard Validator nur bei ausreichend guter Bible-Qualitaet

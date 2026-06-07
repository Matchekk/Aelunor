# Entity Guard Reporting

`scripts/report_entity_guard.py` wertet gespeicherte Entity-Guard-Reports aus
Campaign-Turns aus. Das Script ist read-only: Es laedt Campaign-JSONs, schreibt
nichts zurueck und normalisiert keine Saves.

## Beispielaufrufe

```powershell
python scripts/report_entity_guard.py
python scripts/report_entity_guard.py --campaign-id camp_123
python scripts/report_entity_guard.py --json
python scripts/report_entity_guard.py --out reports/entity_guard_report.md
python scripts/report_entity_guard.py --min-status generic --limit 50
```

## Was ausgewertet wird

Das Script sucht defensiv nach Guard-Daten in:

- `turn.entity_guard`
- `turn.prompt_payload.entity_guard`
- `turn.debug.entity_guard`
- `turn.meta.entity_guard`

Unterstuetzt werden flache Reports mit `summary`/`reports` sowie gestufte
Reports mit `narrator`, `extractor` und `merged`.

## Report-Inhalte

Der Markdown-Report enthaelt:

- globale Summary
- Status-Verteilung
- Breakdown nach Entity Type
- haeufigste Problemnamen
- niedrigste Scores
- Forbidden-/Avoid-Term-Aggregation
- Campaign Breakdown
- konkrete Beispiele mit Reasons und Source Paths

Mit `--json` wird dieselbe Auswertung maschinenlesbar ausgegeben.

## Warum read-only?

Die Reports dienen zur Beobachtung in Longruns und Reviews. Sie sollen zeigen,
ob neue Namen world-bible-kompatibel, weak, generic oder forbidden sind, ohne
laufende Kampagnen zu veraendern.

## Spaetere Nutzung

Die Daten koennen spaeter helfen bei:

- Soft Sanitizer-Hinweisen
- Hard Validator-Regeln
- Runtime World-Bible Extensions
- Review-Scripts fuer Longruns
- Entity-Quarantine-Entscheidungen

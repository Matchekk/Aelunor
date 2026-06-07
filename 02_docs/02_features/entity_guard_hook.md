# Entity Guard Hook v1

Der Entity Guard Hook sammelt benannte Entitaeten aus Turn-Patches und laesst
sie vom Entity Guard gegen die World Bible bewerten. Der Hook beobachtet nur:
keine Rejects, keine Umbenennung, keine UI-Warnung und keine LLM-Retry-Logik.

## Guard vs. Hook

- `entity_guard.md` beschreibt die Namensbewertung gegen World-Bible-Signale.
- Dieser Hook beschreibt, woher Namen im Turn-/Patch-Flow gesammelt werden und
  wo der kompakte Report gespeichert wird.

## Gesammelte Patch-Felder

Der Hook sammelt defensiv:

- `items_new[*].name`
- `characters.<slot>.skills_set|skills_add|skills_update`
- `character_updates.<slot>.skills_set|skills_add|skills_update`
- `characters.<slot>.class_set|class_update|class_current.name`
- `map_add_nodes[*].name|label`
- `map.nodes_add[*].name|label`
- `locations_add[*].name`
- `scenes_add[*].name`
- `plotpoints_add[*].title|name`
- `plotpoints_update[*].title|name`
- `factions_add[*].name`
- `factions_update[*].name`
- `characters.<slot>.faction_join.name`
- `characters.<slot>.faction_memberships[*].name`

Kaputte oder fehlende Patch-Daten werden ignoriert.

## Report

Der Hook erzeugt kompakte Reports fuer:

- `narrator`
- `extractor`
- `merged`

Gespeichert wird der Report im Turn-Record unter `entity_guard` und zusaetzlich
im `prompt_payload.entity_guard`. Reports behalten Summary und eine begrenzte
Anzahl kleiner Einzelreports.

## Keine Rejects

Auch `forbidden` oder `generic` blockiert in v1 keinen Turn. Das System sammelt
nur Beobachtbarkeit fuer Longruns, Reviews und spaetere Guardrails.

## Spaetere Schritte

Moegliche Folgearbeiten:

- Dev Review Script fuer Guard-Findings
- Soft Sanitizer-Hinweise
- Hard Validator-Regeln
- Runtime World-Bible Extensions
- Entity Quarantine

Das aktuelle read-only Reporting-Script ist in `entity_guard_reporting.md`
beschrieben.

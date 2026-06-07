# World Bible v1

Die World Bible ist die kanonische Identitaets-, Sprach-, Naming-, Metaphysik-
und Stilquelle einer Kampagne. Sie soll verhindern, dass Namen, Skills, Items,
Races, Beasts, Orte, Fraktionen oder magische Begriffe frei generisch entstehen.

## State-Pfad

Die Bible liegt im Campaign-State unter:

```json
{
  "state": {
    "world": {
      "bible": {}
    }
  }
}
```

Alte Saves ohne diesen Block bleiben ladbar. Die Campaign-Normalisierung setzt
immer eine v1-Shape und erzeugt nach abgeschlossenem World-Setup eine
deterministische Fallback-Bible aus der Setup-Summary.

## v1-Shape

Version 1 enthaelt mindestens:

- `created_from_setup` fuer Theme, Ton, Weltgesetze, Konflikt und Setup-Rohdaten.
- `identity` fuer Weltname, Pitch, Hook und verbotene generische Stimmung.
- `linguistics` fuer Weltsprachen, Race-Sprachen, Ortsaliasse und Verstehen.
- `naming_rules` fuer People, Orte, Regionen, Ruinen, Fraktionen, Skills, Items,
  Beasts und Titel.
- `metaphysics`, `elements`, `progression`, `races_and_beasts`, `factions`,
  `regions`, `items`, `tone_and_style`, `ui_theme_hints`, `runtime_controls`
  und `revision`.

## Race Linguistics

Intelligente Races oder kulturell eigenstaendige Spezies duerfen eigene Sprache,
Sprachfamilie oder Namenslogik besitzen. Ein Eintrag unter
`linguistics.race_languages` normalisiert Endonym, Exonym, Lautbild, Roots,
Naming-Patterns und Translation-Verhalten.

Schwaches Sprachverstaendnis darf Root-Bedeutungen erkennen, aber Kategorie oder
kulturellen Kontext falsch lesen.

## Place Aliases

`linguistics.place_name_aliases` verbindet einen kanonischen Ort mit
mehrsprachigen Namen. Ein Alias kann literal meaning, cultural meaning,
verwendenede Gruppen und wahrscheinliche Fehlinterpretationen speichern.

So kann zum Beispiel ein Common-Name und ein Race-Endonym derselben Stadt spaeter
im Codex aufgeloest werden, ohne beide als getrennte Orte zu behandeln.

## Generische Namen

Generische Fantasy-Begriffe wie `Feuerball`, `Heiltrank`, `Magiergilde`,
`Goblinhoehle`, `Schattenklinge`, `Eisdrache`, `Kriegerklasse`, `Elfenreich`
oder `Dunkler Wald` sind zu vermeiden, sofern sie nicht durch Weltlogik,
Sprache, Material, Kosten, Herkunft oder Codex-Discovery umgedeutet werden.

## Geheimhaltung

`runtime_controls.secret_sections_hidden_from_players` markiert, dass Teile der
Bible spaeter fuer Spieler verborgen bleiben koennen. Die Bible ist trotzdem
kanonische Quelle fuer Backend-Generierung und Prompt-Zusammenfassungen.

## Nutzung durch spaetere Systeme

Turn-Prompts sollen die kompakte World-Bible-Summary nutzen. Generatoren fuer
Skills, Klassen, Items, Races, Beasts, Fraktionen, Orte und Titel sollen Namen
aus `identity`, `linguistics`, `naming_rules`, `metaphysics`, `progression`,
`races_and_beasts`, `items` und `tone_and_style` ableiten.

Die Prompt-Einbindung ist in `context_injection.md` beschrieben.
Der diagnostische Namens- und Entity-Check ist in `entity_guard.md` beschrieben.
Der beobachtende Patch-Hook fuer neue Entitaeten ist in `entity_guard_hook.md` beschrieben.
Die read-only Qualitaetsauswertung der Bible ist in `world_bible_quality_reporting.md` beschrieben.

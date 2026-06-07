# Living Character System v1

Das Living Character Profile macht Charaktere wiedererkennbar, ohne das
technische Character Sheet zu ersetzen. Nach mehreren Turns soll ein Charakter
typisch handeln koennen, ohne beliebig zu driften.

## State-Pfad

Das Profil liegt pro Charakter unter:

```json
{
  "state": {
    "characters": {
      "slot_1": {
        "living_profile": {}
      }
    }
  }
}
```

Alte Saves ohne `living_profile` bleiben ladbar. Die Character-Normalisierung
setzt eine v1-Shape und erzeugt bei fehlendem Profil einen deterministischen
Fallback aus vorhandenen Character-Daten.

## Sheet vs. Living Profile

Technische Felder bleiben die Quelle fuer Regeln, Zahlen und Inventar:

- `bio`
- `attributes`
- `resources`
- `skills`
- `class_current`
- `inventory`
- `equipment`
- `injuries`
- `scars`
- `journal`
- `progression`

Das Living Profile beschreibt Identitaet, Verhalten, Sprache, soziale Muster,
Motivation, Konflikte, Wachstum und Konsistenzregeln. Es ist kein Ersatz fuer
mechanische Daten.

## Genreoffenheit

Aelunor ist `Your RPG Story`. Das Profil darf Fantasy-, Cyberpunk-, Mystery-,
Piraten-, Superhelden-, Survival- oder eigene Settings tragen. Alte Felder wie
`earth_life`, `isekai_price` oder `earth_items` koennen genutzt werden, wenn sie
existieren, sind aber keine Pflichtannahme.

## Typical Patterns

`behavior_model.typical_patterns` ist der Kern. Ein Pattern besteht aus:

- `trigger`
- `reaction`
- `cost`
- `tell`
- `confidence`

Das System speichert nicht nur Traits, sondern wiedererkennbare Muster:
Wann reagiert der Charakter wie, woran sieht man es, und was kostet es?

## Speech Model

`speech_model` beschreibt Stimme, Satzstil, Wortschatz, Tics, Humor,
Formalitaet, emotionale Lecks und Sprachprofile. Es soll Dialoge konsistent
machen, ohne Spielerentscheidungen zu ersetzen.

## Roleplay Rules

Fuer Spielercharaktere gilt:

- KI darf Mikroreaktionen andeuten.
- KI darf typische Impulse vorschlagen.
- KI darf Stimmung und koerperliche Reaktionen beschreiben.
- KI darf keine grossen Entscheidungen ueberschreiben.
- KI darf geschuetzte Charakterfakten nicht aendern.
- KI darf keine harte Persoenlichkeitswende ohne Setup- oder Storygrund setzen.

## Spaetere Turn-Pipeline-Nutzung

Spaetere Turn-Prompts sollen die kompakte Living-Profile-Summary nutzen. Eine
automatische Aktualisierung aus Turn-Historie, Drift-Validatoren, UI und
LLM-basierte Profilgenerierung gehoeren in spaetere PRs.

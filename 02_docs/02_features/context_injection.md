# Context Injection v1

Context Injection bringt World Bible v1 und Living Character Profile v1 kompakt
in den Turn-Prompt. Ziel ist Konsistenz: jede Kampagne bleibt in ihrer eigenen
Welt-DNA, und Spielercharaktere bleiben wiedererkennbar.

## Prompt-Bloecke

Der Turn-Prompt erhaelt einen Zusatzblock:

- `WORLD BIBLE SUMMARY`
- `ACTIVE CHARACTER LIVING SUMMARY`
- `PARTY LIVING SUMMARY`
- `STYLE AND CONSISTENCY GUARD`

Der kombinierte Block liegt als Text im User-Prompt und wird zusaetzlich im
Prompt-Payload unter `world_character_context` gespeichert.

## Kompakt statt vollstaendiger State

Die Injection nutzt kurze Summary-Funktionen. Es werden keine vollstaendigen
Bible-, Character- oder Campaign-Objekte erneut in den Prompt gedumpt. Das haelt
den Kontext pruefbar, kuerzbar und stabil.

## World Bible Guard

Die World Bible ist verbindlich fuer neue Namen, Sprachen, Ortsaliasse, Skills,
Items, Monster, Races, Fraktionen, Titel und magische Begriffe. Generische
Fantasy-/RPG-Begriffe sollen vermieden werden, wenn die Bible spezifischere
Begriffe ermoeglicht.

Race-Linguistik und Place-Aliases duerfen Teilverstaendnis oder
Fehlinterpretationen erzeugen, wenn ein Charakter eine Sprache nur schwach
versteht.

## Living Profile Guard

Living Profiles liefern typische Muster, Stimme, Motivation und Grenzen. Sie
sind Leitplanken fuer Mikroreaktionen und wiedererkennbare Impulse, aber keine
zweite Story-Ausgabe und kein Ersatz fuer Spielerentscheidungen.

## Spieler-Kontrollgrenzen

Bei Spielercharakteren darf die KI:

- Mikroreaktionen andeuten.
- typische Impulse vorschlagen.
- Koerpersprache, Unsicherheit, Versuchung oder innere Spannung zeigen.

Die KI darf keine grosse Entscheidung, keinen Verrat, keinen Mord, keine
Romanze, keinen Skill-Einsatz und kein freiwilliges Opfer ohne passende
Spieleraktion setzen.

## Spaetere Erweiterungen

Moegliche Folgearbeiten:

- Entity Name Guard, siehe `entity_guard.md`
- Living Profile Update nach Turns
- Pattern Extraction aus Turn-Historie
- Codex Discovery fuer Alias- und Sprachaufloesung

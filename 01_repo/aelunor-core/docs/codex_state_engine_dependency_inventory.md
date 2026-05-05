# Codex / State Engine Dependency Inventory

## Ziel

Diese Datei haelt die aktuellen Kopplungen zwischen `app/services/world/codex.py`,
`app/services/state_engine.py`, `app/services/turn_engine.py` und `app/main.py`
fest. Sie soll spaetere Refactorings absichern, bevor globale Injektion,
Codex-Normalisierung, World State, NPC-Codex, Elements und Progression getrennt
werden.

## Aktuelle Architektur-Risiken

- `app/services/state_engine.py` ist weiterhin ein God Module. Es enthaelt
  unter anderem Character State, Skills, Progression, World Normalisierung,
  Elementlogik, Patch-/Canon-Hilfen, Persistence, Claims und LLM-nahe Logik.
- `configure(main_globals)` mit `globals().update(main_globals)` macht
  Abhaengigkeiten unsichtbar. Funktionen wirken lokal, brauchen aber Symbole,
  die erst nach `app.main`-Import oder Service-Wiring vorhanden sind.
- `app/services/world/codex.py` ist fachlich ein sinnvoller Codex-Schnitt, haengt
  aber fuer Race-, Beast-, Element-, Skill- und NPC-Normalisierung weiter an
  injizierten Symbolen aus dem alten Kern.
- Das Risiko betrifft besonders Save-State-Konsistenz: Codex-Eintraege,
  World-Profile, NPCs, Element-Aliase, Skill-Elemente und Progression-Felder
  koennen bei Refactorings auseinanderlaufen, wenn die impliziten Contracts
  nicht vorher durch Tests beschrieben sind.

## Implizite Abhaengigkeiten von `world/codex.py`

| Funktion | Benoetigte globale Symbole | Vermutete Quelle | Risiko | Spaetere Entkopplungsidee |
| --- | --- | --- | --- | --- |
| `normalize_world_codex_structures` | `normalize_race_profile`, `normalize_beast_profile`, `normalize_element_profile`, `ELEMENT_CORE_NAMES`, `element_sort_key`, `build_element_alias_index`, `normalize_element_relations`, `normalize_element_class_paths`, `CODEX_DEFAULT_META`, `deep_copy`, Codex-Konstanten | vor allem `state_engine.py` und `app/main.py` via `state_engine.configure(...)` | Hoch: World-Profile, Codex-Defaults, Element-Aliase und Class Paths werden in einem Schritt normalisiert. Kleine Aenderungen koennen Save-State-Struktur und View-Erwartungen brechen. | Zuerst Race-/Beast-/Element-Normalisierung in explizite World-Module verschieben, dann `normalize_world_codex_structures` ueber kleine Ports/Dependency-Objekte verdrahten. |
| `normalize_npc_codex_state` | `normalize_npc_entry`, `normalize_element_id_list`, `normalize_resource_name`, `normalize_dynamic_skill_state`, `normalize_skill_elements_for_world`, `normalize_npc_alias` | `state_engine.py`, `world/progression.py`, `world/npc.py`, globale Codex-Konfiguration | Hoch: NPCs, Skills und Elementlisten werden gemeinsam bereinigt; fehlerhafte Alias- oder Elementauflosung kann NPC-Codex und Skill-State veraendern. | NPC-Codex-Service mit explizitem ElementResolver und SkillNormalizer einfuehren. |
| `normalize_npc_entry` | `npc_id_from_name`, `NPC_STATUS_ALLOWED`, `normalize_class_current`, `normalize_resource_name`, `normalize_skill_store`, `next_character_xp_for_level`, `deep_copy` | `world/npc.py`, `world/progression.py`, `state_engine.py`, `app/main.py` | Mittel bis hoch: Die Funktion normalisiert Identitaet, Status, Class, Skills, XP und Ressourcen in einem Dict-Contract. | NPC-State-Model/Validator isolieren; Skill- und Class-Normalisierung als explizite Collaborators uebergeben. |
| `codex_blocks_for_level` | `CODEX_KNOWLEDGE_LEVEL_MIN`, `CODEX_KNOWLEDGE_LEVEL_MAX`, `RACE_BLOCKS_BY_LEVEL`, `BEAST_BLOCKS_BY_LEVEL`, `CODEX_KIND_RACE`, Block-Order-Konstanten | `app/main.py` via globale Injektion oder Test-Harness | Mittel: Knowledge-Level-Grenzen und freigeschaltete Blocks sind Canon-/UI-relevant. | Codex-Konstanten in ein kleines `codex/constants.py` oder Config-Objekt verschieben. |
| `normalize_codex_entry_stable` | `deep_copy`, `CODEX_KIND_RACE`, `CODEX_KNOWLEDGE_LEVEL_MIN`, `CODEX_KNOWLEDGE_LEVEL_MAX`, Block-Order-Konstanten | `app/main.py` und `state_engine.configure(...)` | Mittel: Clamping, bekannte Blocks, bekannte Fakten und Race-/Beast-Spezialfelder muessen stabil bleiben. | Reine Entry-Normalisierung mit explizitem `CodexRules`-Objekt ausstatten. |
| `seed_npc_codex_from_story_cards` | `npc_id_from_name`, `normalize_npc_alias` | `world/npc.py`, im Test aktuell lokal injizierbar | Mittel: Story Cards erzeugen persistente NPC-IDs und Alias-Eintraege; ID-/Alias-Aenderungen wirken reload-uebergreifend. | ID- und Alias-Strategie als kleine NPC-Codex-Abhaengigkeit explizit machen. |

## Empfohlene sichere Refactoring-Reihenfolge

P0:

- Charakterisierungstests sichern.
- Dependency Inventory aktuell halten.
- Keine neuen Features in `state_engine.py` ablegen.

P1:

- Codex-Abhaengigkeiten explizit machen.
- Race-/Beast-/Element-Normalisierung aus `state_engine.py` auslagern.
- Kleine Codex-Service-Grenze einfuehren.

P2:

- Turn Pipeline aufteilen.
- Patch Validator und Patch Sanitizer extrahieren.
- LLM Client isolieren.

P3:

- Typed Domain Models schrittweise einfuehren.
- Live State Backend abstrahieren.

## Tests, die diese Bereiche absichern

- `tests/unit/test_main_state_engine_config.py` prueft, dass `state_engine`,
  `turn_engine` und `world.codex` nach `app.main`-Import konfiguriert sind und
  zentrale injizierte Helper/Domain-Callables vorhanden sind.
- `tests/unit/test_world_codex.py` charakterisiert Alias-Normalisierung,
  Alias-/Exact-Name-Indexe, Entity-Aufloesung, Codex-Entry-Clamping,
  `normalize_world_codex_structures`, NPC-Defaults, NPC-Normalisierung,
  NPC-Alias-Indexe und Story-Card-Seeding.

## Refactoring-Schritt: Explizite Codex Runtime Dependencies

`app/services/world/codex.py` enthaelt jetzt eine interne
`CodexRuntimeDependencies`-Dataclass und die private Funktion `_codex_deps()`.
Diese Schicht ersetzt die globale Injektion nicht. Sie liest weiterhin aus den
aktuell injizierten Modul-Globals, buendelt die benoetigten Collaborators aber an
einer benannten Stelle.

Umgestellt wurden bewusst nur die riskantesten Funktionen:

- `normalize_world_codex_structures`
- `normalize_npc_codex_state`
- `normalize_npc_entry`
- `codex_blocks_for_level`
- `normalize_codex_entry_stable`
- `seed_npc_codex_from_story_cards`

Diese Funktionen beziehen Race-/Beast-/Element-Normalisierung, Element-Alias- und
Relations-Logik, NPC-ID-/Alias-Strategie, Skill-Normalisierung, Class-/Progression-
Hilfen, Codex-Regelwerte, Knowledge-Level-Grenzen, Block-Reihenfolgen und `deep_copy`
jetzt ueber `deps = _codex_deps()`.
Auch die internen Race-/Beast-Kind-Argumente fuer Codex-Entry-Normalisierung in
`normalize_world_codex_structures` laufen ueber `deps.codex_kind_race` und
`deps.codex_kind_beast`, statt dort erneut direkte Kind-Globals zu lesen.

Weiterhin bestehen die globalen Runtime-Abhaengigkeiten und `configure(main_globals)`,
weil diese Aufgabe nur die Abhaengigkeiten sichtbar buendelt und keine Modulgrenzen
oder App-Wiring-Vertraege veraendert. Nicht entkoppelt sind insbesondere:

- Codex-Konstanten und Block-Regeln; sie werden nun ueber `_codex_deps()` gelesen,
  stammen aber weiter aus dem bestehenden globalen Wiring.
- `deep_copy`, NPC-ID-/Alias-Funktionen und Normalizer; sie werden nun ueber
  `_codex_deps()` gelesen, stammen aber weiter aus injizierten Modul-Globals oder
  direkt importierten World-Helfern.
- Die fachlichen Implementierungen fuer Race, Beast, Elements, Skills und Teile der
  Progression, soweit sie noch aus `state_engine.py` oder dessen globalem Wiring
  stammen.

Empfohlener naechster Schritt: Nicht sofort die Turn Pipeline anfassen. Stattdessen
Element-/Skill-Normalisierung als kleine explizite Ports aus `state_engine.py`
herausloesen und diese Ports dann in `CodexRuntimeDependencies` einspeisen.

## Refactoring-Schritt: Element-/Skill-Normalization Ports

`app/services/world/codex.py` buendelt Element- und Skill-Normalisierung jetzt in
kleinen internen Ports:

- `ElementNormalizationPort`
- `SkillNormalizationPort`

`ElementNormalizationPort` enthaelt:

- `normalize_element_profile`
- `element_sort_key`
- `build_element_alias_index`
- `normalize_element_relations`
- `normalize_element_class_paths`
- `normalize_element_id_list`
- `normalize_skill_elements_for_world`

`SkillNormalizationPort` enthaelt:

- `normalize_resource_name`
- `normalize_dynamic_skill_state`
- `normalize_skill_store`

`CodexRuntimeDependencies` referenziert diese Gruppen jetzt ueber
`element_normalization` und `skill_normalization`, statt die Element-/Skill-
Funktionen als flache Einzelattribute zu fuehren.

Umgestellt wurden:

- `normalize_world_codex_structures` fuer Element-Profil, Element-Sortierung,
  Element-Alias-Index, Element-Relations und Element-Class-Paths.
- `normalize_npc_codex_state` fuer NPC-Elementlisten, dynamische Skill-
  Normalisierung, Skill-Element-Abgleich und Resource-Name-Normalisierung.
- `normalize_npc_entry` fuer Resource-Name- und Skill-Store-Normalisierung.

Weiterhin bestehen die globalen Runtime-Abhaengigkeiten und `configure(main_globals)`.
Die Ports implementieren keine neue Fachlogik; sie kapseln nur die bestehenden,
weiterhin injizierten Funktionen. Deshalb ist das noch keine vollstaendige
Entkopplung von `state_engine.py`.

Empfohlener naechster Schritt: Race-/Beast-/Element-Normalisierung schrittweise aus
`state_engine.py` in echte World-Module verschieben. Die Turn Pipeline bleibt
weiterhin ausserhalb dieses Refactoring-Strangs.

## Nicht-Ziele

- Keine Produktionslogikaenderung.
- Keine Entfernung der globalen Injektion in dieser Aufgabe.
- Kein Umbau der Turn Pipeline.
- Keine Aenderung am Save-State-Format.
- Keine Aenderung an API-Vertraegen.
- Keine neuen Features und keine neuen Dependencies.

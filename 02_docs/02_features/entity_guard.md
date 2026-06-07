# Entity Guard v1

Der Entity Guard ist ein sanfter Diagnose-Layer fuer neue Namen und Entitaeten.
Er bewertet, ob ein Name zur World Bible passt oder generisch/problematisch
wirkt. In v1 erzeugt er nur Reports, keine harten Rejects.

## Report-Shape

Ein Report enthaelt:

- `entity_type`
- `name`
- `status`
- `score`
- `reasons`
- `matched_roots`
- `matched_examples`
- `forbidden_terms_found`
- `avoid_terms_found`
- `suggested_direction`
- `requires_review`

Statuswerte sind `ok`, `weak`, `generic`, `forbidden`, `needs_review` und
`unknown`. Der Score liegt zwischen 0 und 100.

## Genutzte World-Bible-Signale

Der Guard sammelt deterministisch Signale aus:

- `linguistics.world_languages.*.common_roots`
- `linguistics.world_languages.*.example_words`
- `linguistics.race_languages.*.common_roots`
- `linguistics.race_languages.*.naming_patterns`
- `linguistics.faction_dialects`
- `naming_rules.*.patterns`
- `naming_rules.*.examples`
- `naming_rules.*.avoid`
- `metaphysics.main_power_name`
- `metaphysics.power_source`
- `metaphysics.power_cost`
- `elements.status_effect_vocabulary`
- `elements.element_language_rules`
- `items.material_vocabulary`
- `items.rarity_language`
- `tone_and_style.forbidden_words`
- `identity.forbidden_generic_feel`

Explizite Beispiele und Naming Rules der World Bible haben Vorrang vor der
internen Generic-Fallback-Liste.

## Naming Modes

Der Guard leitet heuristisch einen `naming_mode` aus der World Bible ab, zum
Beispiel `dark_fantasy`, `isekai_fantasy`, `modern_japanese`,
`superhero_academy`, `cyberpunk`, `pirate`, `modern_global` oder `custom`.

Ein Name ist gut, wenn er zur Bible passt. Nicht jeder gute Name muss
fremdartig oder fantasyhaft sein: In einer Superhelden-Akademie koennen normale
japanische Namen, Hero-Begriffe und Schulnamen passend sein; in Cyberpunk sind
Handles, Konzernnamen und technische Kuerzel oft passend.

## Keine harten Rejects

V1 markiert generische Begriffe wie `Feuerball`, `Heiltrank`, `Goblinhoehle`
oder `Dark Forest`, sofern die World Bible sie nicht explizit erlaubt. Der Guard
benennt Gruende und Review-Bedarf, blockiert aber keine Turns und benennt nichts
automatisch um.

## Spaetere Integration

Folge-PRs koennen den Guard weich in Patch-Sanitizer, Patch-Validator,
Turn-Trace oder eine Entity-Quarantine einhaengen. Harte Rejects sollten erst
kommen, wenn Reports in echten Kampagnen ausreichend stabil und hilfreich sind.

Der beobachtende Turn-/Patch-Hook ist in `entity_guard_hook.md` beschrieben.

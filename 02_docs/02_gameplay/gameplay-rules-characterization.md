# Gameplay Rules Characterization

Stand: Tests in `01_repo/aelunor-core/tests/unit/test_*_rules.py`.

## Items / Equipment

- `slot: weapon` und Weapon-Tags/-Keywords werden als Weapon erkannt.
- Generische Items ohne Slot/Tags passen aktuell nicht in Weapon, Chest oder Offhand.
- Ring-Equipment wird aktuell ueber den Eingabeschluessel `ring` normalisiert; der rohe Key `ring_1` matched nicht.
- Ring-Slots akzeptieren aktuell Ring, Trinket, Amulet und ungetypte Items.
- Trinket/Amulet-Fallback ist asymmetrisch: ungetypte Items passen in beide, Trinkets passen in Amulet, Amulets nicht in Trinket.
- Equipped Items zaehlen beim Carry Weight zusaetzlich zum Inventory. Wenn ein Item in beiden liegt, zaehlt es doppelt.

## Combat / Derived Stats

- Defense = `10 + dex + armor + derived_bonus`.
- Initiative = `dex + derived_bonus`.
- Attack Rating nutzt STR fuer Standardwaffen, DEX fuer Finesse/Ranged und INT fuer Focus; explizites WIS-Scaling nutzt WIS.
- HP 0 setzt `downed=True` und `can_act=False`.
- `stun` als Tag oder Kategorie blockiert Aktion; `paralyzed`/`unconscious` ohne `stun`-Tag blockiert aktuell nicht.
- Frische/heilende schwere Verletzungen blockieren Aktion.

## Skills / Abilities

- Legacy Default Skills starten auf Level 0, XP 0, Rank `-`.
- Default Abilities starten auf Level 1, Rank `F`.
- Legacy Skill-XP wird im Normalizer auf `0..next_xp` geklemmt; Overflow levelt dort nicht weiter.
- `apply_system_xp` und `grant_skill_xp` tragen aktuellen Overflow als Rest-XP weiter.
- Gleiche Skill-Namen und Prefix-Namen werden aktuell im Skill Store zusammengefuehrt.
- Ability-IDs aus Namen sind stabil slugifiziert.

## Resources

- Canonical Resource Mapping: HP/Health/Leben -> `hp`, Stamina/Ausdauer -> `stamina`, Mana/Aether/Ki/Energie -> `aether`.
- `sync_canonical_resources` klemmt Current-Werte in gueltige Max-Bereiche.
- Compat-Views enthalten HP, Stamina, Aether und den benannten Resource-Key.
- Legacy Shadow Writeback entscheidet, ob alte `resources.hp`/`hp`-Shadow-Felder geschrieben oder entfernt werden.
- Nested Resource-Set-Payloads `{current,max}` werden in canonical Runtime-Felder uebersetzt.

## World Time

- Minimal-Meta normalisiert auf Tag 1, Monat 1, Jahr 1, Nacht, leeres Wetter.
- `absolute_day` bestimmt Jahr/Monat/Tag bei 360 Tagen/Jahr und 30 Tagen/Monat.
- Negative oder fehlende Werte werden auf stabile Defaults geklemmt.
- `apply_world_time_advance` synchronisiert `meta.world_time` und Compat-Felder unter `state["world"]`.

## Scene / Location

- Scene-IDs werden aus Namen stabil zu `scene_<slug>`.
- Generische Namen wie `Ort` gelten nicht als plausibel; scene-artige Namen mit Unterstrich sind aktuell noch plausibel.
- `derive_scene_name` nutzt bekannte Scene-/Map-Namen, sonst `Kein Ort` oder die unbekannte Scene-ID.
- Kleine Story-Beispiele fuer Gruppenbewegung liefern stabile Scene Candidates.

## Codex / NPC

- NPC-Aliase entfernen Artikel/Titel wie `die Lady`; `Lady Mara` wird als Alias `mara` erkannt.
- Duplicate NPC-Namen/Aliase werden aktuell auf bestehende IDs gemappt.
- Race-/Beast-Codex-Defaults haben stabile Key-Sets.
- Codex Knowledge Level wird auf den konfigurierten Bereich geklemmt.

## Offene Designentscheidungen

- Soll equipped Carry Weight doppelt zaehlen, wenn Items im Inventory bleiben?
- Soll `ring_1` als roher Equipment-Key akzeptiert werden?
- Sollen `paralyzed` und `unconscious` ohne `stun`-Tag Aktionen blockieren?
- Sollen scene-artige Namen mit Unterstrichen als unplausibel gelten?

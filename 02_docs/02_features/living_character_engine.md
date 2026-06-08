# Living Character Engine (P0/P1)

Die Living Character Engine erweitert Living Profile v1 kompatibel um
verkoerperte, erwartungsbasierte Felder. Figuren entstehen nicht aus
Traitlisten, sondern aus Koerper, Beduerfnis, Erwartung, Beziehung, Kultur,
Biografie und Situation. Sie ist ein **additiver Block** im bestehenden Living
Profile, kein paralleles System.

## Zweck

Verhalten entsteht entlang einer Kausalkette, nicht direkt aus einem Label:

```
Koerperzustand -> Wahrnehmung -> Beduerfnis -> Erwartungsmodell
-> Emotion/Appraisal -> Bindung -> Kultur/Rolle -> Biografie
-> Selbstbild -> Entscheidung -> Sprache -> Memory Update
```

Grundregel: nie vom Label zur Handlung springen. Immer zuerst fragen: Welcher
Koerper? Welche Lage? Welche Erwartung? Welche Beziehung? Welche Norm? Welche
Geschichte? Welche Angst, welches Beduerfnis, welche Maske nach aussen?

## State-Pfad

```text
campaign["state"]["characters"][slot_name]["living_profile"]
```

Das Profil bleibt `version: 1`. Die neuen Bloecke sind optional. Alte Profile
ohne sie bleiben ladbar; `normalize_living_profile` setzt deterministische
Defaults.

## P0/P1-Shape

Neue Bloecke unter `living_profile`:

- `embodiment_model` — `species_id`, `body_baseline`
  (energy_pattern, pain_response, sleep_or_rest_need, temperature_comfort,
  injury_vulnerability, comfort_conditions, stress_body_signals),
  `sensory_profile` (dominant_senses, salience_biases, aversive_cues,
  comfort_cues)
- `needs_model` — `physiological_needs`, `psychological_needs`,
  `social_motives`, `current_pressure`
- `expectation_model` — `learned_priors`, `threat_interpretations`,
  `trust_interpretations`, `prediction_error_notes`
- `attachment_model` — `self_expectation`, `other_expectation`,
  `closeness_strategy`, `conflict_strategy`, `trust_gain_triggers`,
  `betrayal_triggers`, `repair_conditions`
- `body_state` — `energy`, `hunger`, `sleep_debt`, `pain`, `arousal`,
  `muscle_tension`, `breath_pattern`, `temperature_state`, `notes`
- `behavior_policy` — `decision_weights` (need_relief, threat_reduction,
  value_fit, relationship_protection, role_compliance, identity_consistency;
  Floats 0..1), `default_strategies`, `override_conditions`
- `dialogue_policy` — `surface_rule`, `stress_modulation`, `safety_modulation`,
  `deception_notes`, `forbidden_shortcuts`

## Trennung: Species / Culture / Biography / Situation

Die Engine trennt vier Ebenen strikt, um Fantasy-Stereotype zu vermeiden:

1. **Species** — biologische / spekulative Tendenz (`embodiment_model`,
   `species_id`). Tendenzen, keine moralische Essenz.
2. **Culture** — Normen, Status, Tabu (bestehende `world_resonance`,
   `social_model`).
3. **Biography** — gelernte Priors, Wunden, Bindungserwartungen
   (`expectation_model`, `attachment_model`, `origin_context`).
4. **Situation** — aktueller Koerper-/Beziehungskontext (`body_state`,
   `needs_model.current_pressure`).

Verhalten ist die Kreuzung dieser Ebenen, nicht die Ausfaltung eines einzelnen
Traits.

## Ableitung aus dem Character-Setup

`generate_living_profile_fallback` leitet die Felder deterministisch ab:

- `char_age` / `age_bucket` -> Lebensphase / Energiehinweise
- `earth_life` -> formative Priors / cultural friction
- `personality_tags` -> Baseline und Stress-Signaturen (keine harten
  Entscheidungen)
- `strength` -> Kompetenz / `default_strategies` / Decision-Weights
- `weakness` -> Shame-Point / `threat_interpretations` / Stress-Signale
- `current_focus` -> `needs_model.current_pressure`
- `first_goal` -> Want
- `isekai_price` -> initialer `body_state` (z. B. erschoepft, Notes als
  "Ankunftspreis ...")
- `earth_items` / `signature_item` -> comfort cues / Identity Anchors

Regeln: keine klinischen Diagnosen, keine Pop-Psychologie, keine
deterministischen Speziesregeln. Schwaechen wie "Paranoia" erzeugen vorsichtige
Erwartungs-/Stress-Hinweise, kein Krankheitslabel.

## Spieler-Kontrollgrenzen

- `roleplay_rules.ai_may_not_override_major_choices` bleibt `true`.
- `dialogue_policy.forbidden_shortcuts` enthaelt
  "keine grosse Spielerentscheidung ueberschreiben".
- Bei Spielercharakteren nur Mikroreaktionen, Koerpersprache, Stimmung und
  typische Impulse andeuten; keine grosse Entscheidung, kein Verrat, kein Mord,
  keine Romanze, kein Skill-Einsatz ohne passende Spieleraktion.

## Prompt-Nutzung

`build_living_profile_prompt_summary` haengt wenige kompakte Zeilen an:

```text
Body/Needs: <Koerper-/Bedarfslage>.
Expectations: <Bedrohungs-/Vertrauensdeutung>.
Stress/Voice: <Stimme unter Druck>.
```

Es wird kein vollstaendiges Profil-JSON in den Prompt gedumpt.

## Bewusst nicht implementiert (P2/P3)

- keine Relationship Update / Stress / Moral / Arc Engines als Turn-Patches
  (nur dokumentiert/vorbereitet)
- keine vollen SpeciesBehaviorTemplate-Datenbanken fuer Nichtmenschen
- keine MemoryEvents-Salienz-Pipeline
- keine echten LLM-Calls in der Ableitung
- Profile-Updates nach Turns sind nicht P0 und nicht gebaut

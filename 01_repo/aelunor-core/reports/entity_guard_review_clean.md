# Entity Guard Review

Campaigns scanned: 2
Turns scanned: 2
Turns with guard data: 2
Entities assessed: 4
Average score: 92.5
Lowest score: 85
Highest score: 100

Filters:
- exclude_empty: true
- min_turns: 1
- only_smoke: true
Campaigns skipped: 9

## Status Distribution
ok: 4
weak: 0
generic: 0
forbidden: 0
needs_review: 0
unknown: 0

## By Entity Type
entity_type | total | ok | weak | generic | forbidden | needs_review | unknown | avg_score
--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---:
plotpoint | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 92.5

## Problem Names
name | entity_type | count | worst_status | worst_score | example_campaign | example_turn
--- | --- | ---: | --- | ---: | --- | ---

## Worst Reports
score | count | status | entity_type | name | campaign_id | turn_number | reasons
---: | ---: | --- | --- | --- | --- | ---: | ---
85 | 4 | ok | plotpoint | Erste Quirk-Bewertung in Hoshino | camp_ab898a70ae | 1 | Name fits inferred naming mode: superhero_academy.; World Bible has entity-specific naming rules.; Name is structured and not purely generic.
85 | 4 | ok | plotpoint | Hoshino Erstsemester-Bewertung | camp_ab898a70ae | 1 | Name fits inferred naming mode: superhero_academy.; World Bible has entity-specific naming rules.; Name is structured and not purely generic.
100 | 4 | ok | plotpoint | Der Eid von Ssereth-Vael | camp_84a7abdb1a | 1 | Name uses World Bible roots.; Name uses race-language roots.; Name resembles a World Bible naming example.
100 | 4 | ok | plotpoint | Sofort zurück | camp_84a7abdb1a | 1 | Name uses World Bible roots.; Name fits inferred naming mode: dark_fantasy.; World Bible has entity-specific naming rules.

## Problem Terms
term | count | examples
--- | ---: | ---

## Campaign Breakdown
campaign_id | title | turns_scanned | guarded_turns | total_entities | ok | weak | generic | forbidden | needs_review | unknown | avg_score
--- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---:
camp_84a7abdb1a | AI Smoke - Dark Fantasy | 1 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 100.0
camp_ab898a70ae | AI Smoke - Superhero Academy | 1 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 85.0

## Examples

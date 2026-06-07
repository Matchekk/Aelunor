from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SmokeScenario:
    key: str
    title: str
    setup_answers: dict[str, Any]
    character: dict[str, Any]
    actions: list[str]


SCENARIOS: dict[str, SmokeScenario] = {
    "dark-fantasy": SmokeScenario(
        key="dark-fantasy",
        title="AI Smoke - Dark Fantasy",
        setup_answers={
            "theme": "Dark fantasy survival world with invented languages, dangerous magic costs, race linguistics, cursed relics and non-generic locations.",
            "tone": "sakral, kalt, koerperlich, bedrohlich",
            "difficulty": "hart",
            "resource_name": "Veyr",
            "world_structure": "zerbrochene Stadtstaaten an alten Eidstrassen",
            "world_laws": [
                "Magie entsteht aus Erinnerung, Blut und Eid.",
                "Jede Heilung verschiebt Schmerz an einen anderen Ort.",
                "Fremde Ortsnamen koennen dieselbe Stadt aus anderer Kultur meinen.",
            ],
            "central_conflict": "Die letzten warmen Staedte handeln mit Relikten, waehrend Echsenvoelker alte Ortsnamen bewahren.",
            "factions_raw": "Eidwacht; Kalthaendler; Ssar-Keth-Keeper",
            "taboos": "kostenlose Heilung, generische Magiergilden, namenlose Monster",
            "player_count": 1,
        },
        character={
            "name": "Mara Venn",
            "personality": ["trockener Humor", "beschuetzend", "ungeduldig"],
            "goal": "eine Stadt retten, ohne noch einmal jemanden zurueckzulassen",
            "strength": "greift ein, wenn Schwache bedroht werden",
            "weakness": "uebersieht Risiken, wenn jemand verletzt ist",
            "focus": "Relikte, Sprache und Rettung",
            "class_name": "Eidlaeuferin",
            "skill_name": "Veyrgriff",
        },
        actions=[
            "Ich untersuche die fremden Runen am Tor und frage den Echsenmenschen nach dem Namen dieser Stadt.",
            "Ich versuche aus dem gefundenen Relikt eine Faehigkeit zu verstehen.",
            "Ich handle mit einem verwundeten Fremden um Informationen ueber die Kreatur im Wald.",
            "Ich riskiere eine gefaehrliche Technik, um jemanden zu retten.",
        ],
    ),
    "superhero-academy": SmokeScenario(
        key="superhero-academy",
        title="AI Smoke - Superhero Academy",
        setup_answers={
            "theme": "Modern Japanese superhero academy with students, hero names, quirks, support gear, public rankings, school rivalries and training arcs.",
            "tone": "energiegeladen, kompetitiv, warm, mit realen Konsequenzen",
            "difficulty": "mittel",
            "resource_name": "Drive",
            "world_structure": "moderne Akademien, Trainingsarenen, Agenturen und Stadtbezirke",
            "world_laws": [
                "Kraefte sind persoenlich, koerperlich begrenzt und sozial reguliert.",
                "Support Gear darf Faehigkeiten staerken, aber keine Identitaet ersetzen.",
                "Oeffentliche Rankings erzeugen Druck und Rivalitaeten.",
            ],
            "central_conflict": "Schueler muessen Ruhm, Sicherheit und echte Verantwortung ausbalancieren.",
            "factions_raw": "Hoshino Academy; Klasse 1-B; Support Lab; Hero Licensing Board",
            "taboos": "Fantasy-Rassen erzwingen, generische Zauber, entmuendigende Heldenentscheidungen",
            "player_count": 1,
        },
        character={
            "name": "Akira Tanaka",
            "personality": ["analytisch", "ehrgeizig", "hilft unter Druck"],
            "goal": "eine Hero License verdienen, ohne die eigenen Freunde als Sprungbrett zu benutzen",
            "strength": "lernt schnell aus Fehlern",
            "weakness": "will Leistung beweisen, bevor er um Hilfe bittet",
            "focus": "Quirk-Training, Support Gear und Rivalitaet",
            "class_name": "First-Year Hero Candidate",
            "skill_name": "Pulse Step",
        },
        actions=[
            "Ich stelle mich in der ersten Trainingsstunde vor und beobachte die Quirks der anderen.",
            "Ich teste meine Faehigkeit gegen einen Roboter-Dummy.",
            "Ich rede nach dem Training mit einem Rivalen aus Klasse 1-B.",
            "Ich versuche mein Support Gear zu verbessern, ohne die Regeln der Akademie zu brechen.",
        ],
    ),
}

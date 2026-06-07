import json
from typing import Any, Callable, Dict, List, Tuple


def build_actor_resolution_hint(
    *,
    actor: str,
    actor_display: str,
    action_type: str,
    content: str,
    is_first_person_action: Callable[[str], bool],
) -> List[str]:
    actor_resolution_hint = [
        f"Aktiver Actor-Slot: {actor}.",
        f"Aktive Figur dieses Turns: {actor_display}.",
        f"Diese {action_type}-Aktion gehört ausschließlich zu {actor_display}.",
    ]
    if is_first_person_action(content):
        actor_resolution_hint.append(
            f"Erste-Person-Pronomen im Spieltext wie 'ich', 'mich', 'mir' oder 'mein' meinen in diesem Turn immer {actor_display} und niemals eine andere Figur."
        )
    return actor_resolution_hint


def build_turn_user_prompt(
    *,
    campaign: Dict[str, Any],
    actor: str,
    action_type: str,
    content: str,
    context: str,
    turn_mode_guide: Dict[str, str],
    turn_response_json_contract: str,
    display_name_for_slot: Callable[[Dict[str, Any], str], str],
    is_slot_id: Callable[[str], bool],
    is_first_person_action: Callable[[str], bool],
    consistency_context: str = "",
) -> Tuple[str, str, List[str]]:
    actor_display = display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor
    actor_resolution_hint = build_actor_resolution_hint(
        actor=actor,
        actor_display=actor_display,
        action_type=action_type,
        content=content,
        is_first_person_action=is_first_person_action,
    )
    action_packet = {
        "actor": actor,
        "actor_display": actor_display,
        "action_type": action_type,
        "action_type_note": turn_mode_guide[action_type],
        "content": content,
        "actor_resolution_hint": " ".join(actor_resolution_hint),
    }
    user_prompt = (
        "CONTEXT_PACKET(JSON):\n"
        + context
        + ("\n\n" + consistency_context if consistency_context else "")
        + "\n\nOUTPUT-KONTRAKT:\n"
        + turn_response_json_contract
        + "\n\nPLAYER_ACTION(JSON):\n"
        + json.dumps(action_packet, ensure_ascii=False)
        + "\n\nACTOR_AUFLÖSUNG:\n"
        + "\n".join(f"- {line}" for line in actor_resolution_hint)
        + "\n\nAntworte ausschließlich im JSON-Format gemäß OUTPUT-KONTRAKT."
    )
    return user_prompt, actor_display, actor_resolution_hint


def build_turn_system_prompt(
    *,
    system_prompt_base: str,
    turn_mode_guide: Dict[str, str],
    pacing_text: str,
    attribute_prompt_hints: str,
    combat_scaling_context: Dict[str, Any],
    min_story_chars: int,
) -> str:
    return (
        system_prompt_base
        + "\n\nACTION_TYPE-HINWEIS:\n"
        + "\n".join(f"- {mode}: {description}" for mode, description in turn_mode_guide.items())
        + "\n\n"
        + pacing_text
        + "\n\n"
        + attribute_prompt_hints
        + "\nAuthor's Note ist immer bindender Zusatzkontext und liegt im Context Packet unter boards.authors_note.content."
        + "\nJeder sichtbare Text in story und requests muss vollständig auf Deutsch sein. Englische Sätze oder englische UI-Texte sind verboten."
        + "\nDu musst immer direkt auf die letzte Spieleraktion reagieren."
        + "\nGreife in den ersten 1-2 Sätzen die konkrete Aktion oder Aussage des Actors sichtbar auf."
        + "\nINTENT-FIRST ist bindend: Löse die explizite Spielerhandlung zuerst auf, bevor du neue Komplikationen einführst."
        + "\nMISSION-PACING ist bindend: Überspringe keine Zwischenstufen (Infiltration/Ermittlung/Verifikation), außer der Spieler eskaliert explizit."
        + "\nNO-RESET: Ziehe eine laufende Szene fort und starte sie nicht mit denselben Stakes oder derselben Einleitung neu."
        + "\nSystem-/Status-/Info-Aktionen führen primär zu Informationen und nur zu minimaler Umweltdynamik; keine harte Eskalation ohne Anlass."
        + "\nAktive Tarnungen/Coverstories bleiben bestehen, bis der Spieler sie ausdrücklich aufgibt oder die Szene sie glaubwürdig bricht."
        + "\nWenn der Spieltext in der ersten Person formuliert ist, löse 'ich/mich/mir/mein' immer auf den aktuellen Actor-Slot auf."
        + "\nNeue oder veränderte Kräfte, Magien, Waffenkünste und Körperentwicklungen werden im Patch über skills_set oder skills_delta abgebildet."
        + "\nELEMENTSYSTEM ist bindend: Nutze nur Elemente aus world.elements. Wenn keine Relation definiert ist, gilt neutral."
        + "\nElementare Klassen müssen element_id oder element_tags tragen. Skills können elements und element_primary setzen."
        + "\nKlassenpfade sind in world.element_class_paths hinterlegt. Klassenfortschritt soll zu passenden Kernskills führen."
        + "\nWenn du beim aktuellen Actor sichtbar einen neuen getragenen oder gehaltenen Gegenstand einführst, musst du ihn auch im Patch über items_new plus inventory_add oder equipment_set kanonisch festhalten."
        + "\nBei action_type=story ist der Spielertext ein bereits gesetzter Story-Impuls oder kanonischer Beat. Wiederhole oder paraphrasiere ihn nicht fast wörtlich. Nimm ihn als gesetzt und schreibe direkt die unmittelbaren Konsequenzen und die nächste Entwicklung weiter."
        + "\nBei 'Weiter' setzt du exakt am letzten erzählten Beat an und springst nicht zu einer früheren Standardidee zurück."
        + "\nWiederhole niemals frühere GM-Sätze oder fast identische Paraphrasen."
        + "\nEröffne neue Antworten nie mit einer bloßen Wiederholung des zuletzt etablierten Zustands. Starte mit Veränderung, Konsequenz, Reaktion oder neuem Detail."
        + "\nJede Antwort braucht mindestens ein neues konkretes Element, das in den letzten zwei GM-Antworten so noch nicht gesagt wurde."
        + "\nPro Turn maximal eine große neue Hauptkomplikation; vertiefe primär bestehende Konflikte."
        + "\nBeende Antworten mit klarer spielbarer Lage statt mit mehreren rhetorischen Fragen (maximal eine Abschlussfrage)."
        + "\nWenn eine Figur Schaden nimmt, erschöpft wird oder ihre Ressource sichtbar einsetzt, muss der Patch das sofort über hp_delta, stamina_delta oder resources_delta(res) abbilden."
        + "\nWenn eine Figur im Text klar getroffen, verwundet, erschöpft oder magisch ausgelaugt wird und der Patch keine passende Ressourcenänderung enthält, ist die Antwort unvollständig."
        + "\nIn Kampfszenen musst du aktiv vorhandene Ausrüstung, Klasse, Attribute und Skills der beteiligten Figuren berücksichtigen und im Fließtext konkret benennen, statt generische Treffertexte zu schreiben."
        + "\nNutze progression_events im Character-Patch für Fortschritt: type, actor, severity, reason, optional target_skill_id, optional target_class_id, optional skill (für skill_manifestation)."
        + "\nNeue Skills dürfen nur über skills_set oder progression_events(type=skill_manifestation) entstehen. Eine reine Floskel reicht nicht."
        + "\nErzähle Skill-/Klassenfortschritt möglichst nur dann als vollendete Tatsache, wenn im selben Output die passende strukturierte Änderung im Patch enthalten ist."
        + "\nWenn der aktuelle Actor noch keinen Skill besitzt und sich in einer klaren Kampf-/Konfliktszene befindet, soll in hoher Priorität (Richtwert ~80%) eine plausible Skill-Erstmanifestation im Patch landen."
        + f"\nCOMBAT-SKALIERUNG: actor_score={combat_scaling_context.get('actor_score')} threat_score={combat_scaling_context.get('threat_score')} pressure={combat_scaling_context.get('pressure')} ratio={combat_scaling_context.get('ratio')} weighted_ratio={combat_scaling_context.get('weighted_ratio')} element_factor={combat_scaling_context.get('element_factor')}."
        + "\nEs gibt keine Würfel, keine DCs und keine Roll-Requests. requests darf nur clarify, choice oder none enthalten."
        + f"\nDie story muss mindestens {min_story_chars} Zeichen enthalten."
    )

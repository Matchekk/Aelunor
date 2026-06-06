from typing import Dict


def append_context_hint(base: str, hint: str) -> str:
    base = str(base or "").strip()
    hint = str(hint or "").strip()
    if not hint:
        return base
    if not base:
        return hint
    return f"{base} {hint}"

def dynamic_option_description(question_id: str, option: str, context: Dict[str, str]) -> str:
    theme = context.get("theme", "")
    tone = context.get("tone", "")
    world_structure = context.get("world_structure", "")
    difficulty = context.get("difficulty", "")
    monsters_density = context.get("monsters_density", "")
    resource_scarcity = context.get("resource_scarcity", "")
    resource_name = context.get("resource_name", "")
    ruleset = context.get("ruleset", "")
    strength = context.get("strength", "")
    weakness = context.get("weakness", "")
    focus = context.get("current_focus", "")

    if question_id == "theme":
        descriptions = {
            "Dark Isekai (Survival/Horror)": "Zieht den Run in Richtung knapper Flucht, unklarer Gefahr und existenzieller Unsicherheit.",
            "Grimdark Fantasy (Krieg/Fraktionen)": "Stellt Machtblöcke, Verrat und ein zermürbendes großes Konfliktfeld in den Vordergrund.",
            "Monster-Hunt (Jagd/Beute/Upgrade)": "Fokussiert Beutezüge, gefährliche Fährten und spürbaren Fortschritt über besiegte Bedrohungen.",
            "Mystery/Occult (Geheimnisse/Kulte)": "Legt den Schwerpunkt auf verborgene Wahrheiten, Rituale, Kulte und langsames Entschlüsseln.",
            "Dungeon-Crawl (Fallen/Loot/Progress)": "Bringt enge Räume, riskante Vorstöße, Fallen und klaren Vorwärtsdruck in die Szenen.",
            "Sandbox (freie Erkundung)": "Öffnet die Welt stärker, damit Entdeckung, Umwege und selbstgewählte Prioritäten tragen.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Der aktuelle Ton {tone} färbt diese Richtung zusätzlich ein." if tone else "")
    if question_id == "player_count":
        try:
            count = int(option)
        except ValueError:
            count = 1
        if count == 1:
            return "Hält alles eng, persönlich und stark auf eine einzelne Hauptfigur konzentriert."
        if count <= 3:
            return "Gibt jeder Figur klaren Raum und hält die Gruppe trotzdem beweglich."
        return "Erzeugt mehr Gruppendynamik, Reibung und mehrere gleichzeitige Blickwinkel."
    if question_id == "campaign_length":
        descriptions = {
            "Kurz": "Zielt auf einen kompakten Run mit schnellerem Plot-Fortschritt und klaren Meilensteinen (~120 Turns).",
            "Mittel": "Balanciert Fortschritt und Details für längere Kampagnenphasen (~720 Turns).",
            "Unbestimmt": "Kein fixes Endziel; die Kampagne kann offen weiterlaufen, solange der Tisch es will.",
        }
        return descriptions.get(option, "")
    if question_id == "tone":
        descriptions = {
            "Düster-realistisch": "Erdet jede Szene und lässt Gewalt, Hunger und Verlust schwer und glaubwürdig wirken.",
            "Anime-dark (stilisiert, brutal wenn nötig)": "Erlaubt größere Bilder, klare Archetypen und dennoch harte Spitzen im richtigen Moment.",
            "Brutal/gnadenlos": "Macht die Welt härter, direkter und weniger verzeihend in ihren Konsequenzen.",
            "Melancholisch/hoffnungslos": "Schiebt Trauer, Verfall und ein langsames Gefühl des Untergehens in den Vordergrund.",
            "Zynisch/dreckig": "Betont Niedertracht, schmutzige Deals und Figuren, die eher überleben als glänzen wollen.",
            "Mystisch/bedrohlich": "Lässt vieles größer, älter und unheilvoller wirken, auch wenn die Gefahr noch unsichtbar ist.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Passt stark zu {theme}." if theme else "")
    if question_id == "difficulty":
        descriptions = {
            "Gritty": "Fehler tun weh, aber die Welt lässt noch Luft für knappe Erholung und kluge Auswege.",
            "Brutal": "Konsequenzen sitzen tiefer, Ressourcen kippen schneller und falsche Risiken rächen sich spürbar.",
            "Hardcore": "Die Welt gönnt kaum Puffer; selbst gute Pläne müssen mit maximalem Druck gerechnet werden.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Mit Ton {tone} wirkt das noch kompromissloser." if tone else "")
    if question_id == "monsters_density":
        descriptions = {
            "Selten": "Monstern begegnet man weniger oft, dafür wirken einzelne Auftritte größer und markanter.",
            "Regelmäßig": "Hält stetigen Druck in der Welt, ohne jede Szene automatisch in Kampf zu kippen.",
            "Überall": "Macht Bewegung selbst zum Risiko und drückt den Run stark in Richtung permanenter Bedrohung.",
            "Situativ (nur in bestimmten Zonen)": "Erlaubt ruhige Zwischenräume und klar abgegrenzte Höllenzonen mit eigenem Profil.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Das kontrastiert gerade mit der Knappheit {resource_scarcity}." if resource_scarcity else "")
    if question_id == "resource_scarcity":
        descriptions = {
            "Niedrig": "Lässt den Run freier atmen und verschiebt den Druck eher auf Konflikte als auf Versorgung.",
            "Mittel": "Hält Versorgung relevant, ohne jede Entscheidung sofort in blanken Mangel zu verwandeln.",
            "Hoch": "Macht Vorräte, Licht, Wasser und Werkzeug schnell zu eigenen Story-Treibern.",
            "Extrem": "Schon der nächste Tag wird zur Frage von Kälte, Hunger, Improvisation und bitteren Prioritäten.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Monsterdichte: {monsters_density}." if monsters_density else "")
    if question_id == "resource_name":
        descriptions = {
            "Aether": "Wirkt archaisch-mystisch und passt gut zu Relikten, Siegeln und uralten Strukturen.",
            "Mana": "Klingt klassisch-fantastisch und hält Magie als gut lesbaren Kernbegriff.",
            "Ki": "Schiebt Fokus auf Körperdisziplin, innere Strömung und kontrollierte Technik.",
            "Chakra": "Betont spirituelle Zentren, innere Balance und kultische Systeme.",
            "Prana": "Färbt die Welt stärker lebensenergetisch und naturverbunden.",
            "Flux": "Wirkt technomagisch, instabil und experimentell.",
            "Essenz": "Fühlt sich roh, alchemistisch und existenziell an.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Aktuell gesetzt: {resource_name}." if resource_name else "")
    if question_id == "healing_frequency":
        descriptions = {
            "Selten": "Verletzungen bleiben länger relevant und schreiben sich tiefer in den Szenenverlauf ein.",
            "Normal": "Hält Schaden spürbar, ohne den Run in Dauerlähmung zu drücken.",
            "Häufig": "Erlaubt aggressiveres Spiel, weil Rückschläge eher abgefangen werden können.",
        }
        return append_context_hint(descriptions.get(option, ""), f"In Kombination mit {difficulty} bleibt das gut lesbar." if difficulty else "")
    if question_id == "ruleset":
        descriptions = {
            "Konsequent": "Lässt Entscheidungen direkt und klar zurückschlagen, ohne Ausweichen über Zufall oder Gnade.",
            "Dramatisch": "Gewichtet emotionale Wendungen und bittere Kosten stärker als nüchterne Härte.",
            "Erbarmungslos": "Spielt jede falsche Entscheidung brutal aus und hält den Druck permanent hoch.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Gerade bei Wertebereich {context.get('attribute_range', '')} wirkt das besonders klar." if context.get("attribute_range") else "")
    if question_id == "attribute_range":
        descriptions = {
            "1-10": "Bleibt kompakt und schnell lesbar; kleine Unterschiede wirken sofort bedeutsam.",
            "1-20": "Gibt etwas feinere Abstufungen, ohne das Blatt mit Zahlen zu überfrachten.",
            "1-100": "Erlaubt sehr feine Skalen, große Schwankungen und detailreiche Progression.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Mit {ruleset} bleibt die Skala gut greifbar." if ruleset else "")
    if question_id == "outcome_model":
        descriptions = {
            "Erfolg / Misserfolg": "Hält Szenen direkter und klarer, mit harten Kanten zwischen gelungen und misslungen.",
            "Erfolg / Teilerfolg / Misserfolg-mit-Preis": "Gibt dem GM mehr graue Zwischenräume, Kosten und bittere Kompromisse.",
            "Cinematic (weniger Würfe, harte Konsequenzen)": "Setzt auf weniger Unterbrechung und größere Wendepunkte pro Entscheidung.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Passt gut zu {tone}." if tone else "")
    if question_id == "world_structure":
        descriptions = {
            "Hub + Dungeons": "Schafft einen wiederkehrenden sicheren Kern und klare Ausbrüche in gefährliche Zonen.",
            "Zonen/Regionen (mit Grenzen/Fog of War)": "Betont Fortschritt über erkundete Grenzen und Stück-für-Stück-Enthüllung.",
            "Offene Welt (Sandbox)": "Lässt die Gruppe stärker selbst treiben, umleiten und Prioritäten setzen.",
            "Reise-Kampagne (Road-Movie)": "Schiebt Bewegung, Weggefährten, Durchgangsorte und stetigen Ortswechsel nach vorn.",
            "Stadtzentriert (Intrigen/Fraktionen)": "Verdichtet Drama auf Beziehungen, Fraktionen, Deals und Machtspiele an einem Knotenpunkt.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Der bisherige Ton {tone} bekommt darin einen klaren Raum." if tone else "")
    if question_id == "world_laws":
        hint = "Verankert ein dauerhaftes Weltgesetz, das Entscheidungen und Risiken fortlaufend färbt."
        if theme:
            hint = append_context_hint(hint, f"Gerade im Rahmen von {theme} kann das starke Kontraste erzeugen.")
        return hint
    if question_id == "char_gender":
        return append_context_hint("Legt die Identität der Figur fest, ohne ihre Spielstärke oder Klasse vorzugeben.", f"Die Welt {theme} reagiert dann auf genau diese Figur." if theme else "")
    if question_id == "char_age":
        descriptions = {
            "Teen (16-19)": "Bringt frühe Härte, Unfertigkeit und oft mehr rohen Trotz in den Run.",
            "Jung (20-25)": "Fühlt sich beweglich, suchend und offen für schnelle Richtungswechsel an.",
            "Erwachsen (26-35)": "Gibt der Figur greifbare Reife, Entscheidungen mit Gewicht und klare Altlasten.",
            "Älter (36+)": "Stärkt Lebenserfahrung, Müdigkeit, Narben und eine andere Art von Autorität.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Passt gut zu Fokus {focus}." if focus else "")
    if question_id == "personality_tags":
        return append_context_hint("Setzt eine spürbare Charakterkante, die in Dialogen, Risiken und Gruppenspannung sichtbar werden kann.", f"Besonders interessant neben {weakness}." if weakness else "")
    if question_id == "strength":
        return append_context_hint("Macht klar, worin die Figur unter Druck verlässlich glänzen darf.", f"In dieser Welt mit {theme} kann das besonders tragen." if theme else "")
    if question_id == "weakness":
        return append_context_hint("Gibt der Welt einen echten Hebel, um Druck auf die Figur auszuüben.", f"Das reibt sich spannend mit Stärke {strength}." if strength else "")
    if question_id == "current_focus":
        return append_context_hint("Bestimmt, worauf die Figur in den ersten Szenen instinktiv zusteuert.", f"Zusammen mit Stärke {strength} entsteht sofort eine klare Dynamik." if strength else "")
    if question_id == "class_start_mode":
        return "Legt fest, ob die Klasse sofort entsteht, von dir direkt definiert wird oder sich erst in der Story bildet."
    if question_id == "isekai_price":
        return append_context_hint("Sorgt dafür, dass die Ankunft sofort eine greifbare Narbe oder Last hinterlässt.", f"Bei Schwäche {weakness} kann das besonders wehtun." if weakness else "")
    return ""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("ISEKAI_BASE_URL", "http://localhost:8080").rstrip("/")
DATA_CAMPAIGNS_DIR = ROOT / "data" / "campaigns"
RUN_OUTPUT_DIR = ROOT / "data" / "automation_runs"
CONTINUE_STORY_MARKER = "__CONTINUE_STORY__"
DEFAULT_TIMEOUT = 240
DEFAULT_PROFILE = "knight"


class LongRunError(RuntimeError):
    pass


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def api(
    method: str,
    path: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers=headers,
        json=body,
        timeout=timeout,
    )
    if response.status_code >= 400:
        detail = response.text.strip()
        try:
            payload = response.json()
            detail = str(payload.get("detail") or payload)
        except Exception:
            pass
        raise LongRunError(f"{method} {path} -> {response.status_code}: {detail}")
    if not response.text.strip():
        return {}
    return response.json()


def viewer_headers(player_id: str, player_token: str) -> Dict[str, str]:
    return {
        "X-Player-Id": player_id,
        "X-Player-Token": player_token,
    }


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def campaign_file(campaign_id: str) -> Path:
    return DATA_CAMPAIGNS_DIR / f"{campaign_id}.json"


def latest_run_log_for_campaign(campaign_id: str) -> Path:
    return RUN_OUTPUT_DIR / f"{campaign_id}.jsonl"


def session_meta_file(campaign_id: str) -> Path:
    return RUN_OUTPUT_DIR / f"{campaign_id}.session.json"


def choose_option(preview_entry: Dict[str, Any], preferred: Any) -> Dict[str, Any]:
    answer = dict(preview_entry["answer"])
    if isinstance(preferred, list):
        answer["selected"] = preferred
        answer["other_values"] = []
        answer["other_text"] = ""
    else:
        answer["value"] = preferred
        answer["selected"] = preferred
        answer["other_text"] = ""
    return answer


def mutate_world_preview(preview_answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    preferred = {
        "theme": "Klassische Fantasy (Mittelalter/Abenteuer)",
        "player_count": "1",
        "tone": "Düster-realistisch",
        "difficulty": "Brutal",
        "death_possible": True,
        "monsters_density": "Regelmäßig",
        "resource_scarcity": "Mittel",
        "healing_frequency": "Selten",
        "ruleset": "Konsequent",
        "attribute_range": "1-20",
        "outcome_model": "Erfolg / Teilerfolg / Misserfolg-mit-Preis",
        "world_structure": "Zonen/Regionen (mit Grenzen/Fog of War)",
        "central_conflict": (
            "Ein altes Königreich zerfällt zwischen Monsterdruck, verfluchten Grenzlanden "
            "und rivalisierenden Orden, die nach verbotener Magie greifen."
        ),
        "factions": (
            "1. Die Aschenkronen: Wollen das gefallene Reich unter eiserner Herrschaft neu errichten.\n"
            "2. Der Runenklerus: Jagt Relikte, bewahrt Magie und opfert dafür Menschenleben.\n"
            "3. Die Schwarze Schar: Plündert Grenzlande und dient namenlosen Wesen aus Ruinen."
        ),
        "taboos": "",
    }
    multi = {
        "world_laws": [
            "Magie hat einen Preis (Blut/Erinnerung/Zeit)",
            "Nacht ist tödlich (Jagdgebiet der Schatten)",
        ],
    }
    mutated: List[Dict[str, Any]] = []
    for entry in preview_answers:
        qid = entry["question_id"]
        if qid in multi:
            mutated.append(choose_option(entry, multi[qid]))
        elif qid in preferred:
            mutated.append(choose_option(entry, preferred[qid]))
        else:
            mutated.append(dict(entry["answer"]))
    return mutated


def mutate_character_preview(preview_answers: List[Dict[str, Any]], profile: str) -> List[Dict[str, Any]]:
    profile_key = (profile or DEFAULT_PROFILE).strip().lower()
    preferred = {
        "char_name": "Matchek",
        "char_gender": "Männlich",
        "class_start_mode": "Erst in der Story",
        "class_seed": "",
        "class_custom_name": "",
        "class_custom_description": "",
        "class_custom_tags": "",
    }
    if profile_key == "knight":
        preferred.update(
            {
                "class_start_mode": "Ich definiere selbst",
                "class_seed": "Ritter, Stahl, Schild, Pflicht, Disziplin",
                "class_custom_name": "Eisenritter",
                "class_custom_description": "Ein disziplinierter Frontkämpfer, der mit Schild, Klinge und eiserner Haltung Gefahren standhält.",
                "class_custom_tags": "stahl\nritter\ndisziplin\nfront",
            }
        )
    mutated: List[Dict[str, Any]] = []
    for entry in preview_answers:
        qid = entry["question_id"]
        if qid in preferred:
            mutated.append(choose_option(entry, preferred[qid]))
        else:
            mutated.append(dict(entry["answer"]))
    return mutated


def patch_world_resource_name(campaign_id: str, resource_name: str) -> None:
    path = campaign_file(campaign_id)
    if not path.exists():
        raise LongRunError(f"Kampagnendatei nicht gefunden: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("setup", {}).setdefault("world", {}).setdefault("summary", {})["resource_name"] = resource_name
    payload.setdefault("state", {}).setdefault("world", {}).setdefault("settings", {})["resource_name"] = resource_name
    payload["state"]["world"]["settings"].setdefault("consequence_severity", "hoch")
    payload["state"]["world"]["settings"].setdefault("progression_speed", "normal")
    payload["state"]["world"]["settings"].setdefault("evolution_cost_policy", "leicht")
    payload["state"]["world"]["settings"].setdefault("offclass_xp_multiplier", 0.7)
    payload["state"]["world"]["settings"].setdefault("onclass_xp_multiplier", 1.0)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def inject_automation_player(campaign_id: str, display_name: str = "Codex-Auto") -> Dict[str, str]:
    path = campaign_file(campaign_id)
    payload = load_json(path)
    player_id = f"player_auto_{campaign_id[-6:]}"
    player_token = f"auto_token_{campaign_id[-10:]}"
    token_hash = __import__("hashlib").sha256(player_token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    payload.setdefault("players", {})[player_id] = {
        "display_name": display_name,
        "player_token_hash": token_hash,
        "joined_at": now,
        "last_seen_at": now,
    }
    if payload.get("claims"):
        for slot_name, owner in list((payload.get("claims") or {}).items()):
            if owner:
                payload["claims"][slot_name] = player_id
                break
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "campaign_id": campaign_id,
        "player_id": player_id,
        "player_token": player_token,
        "injected": True,
    }
    session_meta_file(campaign_id).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def save_session_meta(meta: Dict[str, Any]) -> None:
    session_meta_file(meta["campaign_id"]).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session_meta(campaign_id: str) -> Dict[str, Any]:
    path = session_meta_file(campaign_id)
    if not path.exists():
        raise LongRunError(f"Session-Metadatei fehlt: {path}")
    return load_json(path)


def latest_turn(campaign: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    turns = campaign.get("active_turns") or []
    return turns[-1] if turns else None


def resource_label(campaign: Dict[str, Any]) -> str:
    return (
        str((((campaign.get("state") or {}).get("world") or {}).get("settings") or {}).get("resource_name") or "Aether")
        .strip()
        or "Aether"
    )


def pick_scene_name(campaign: Dict[str, Any], slot_id: str) -> str:
    for card in campaign.get("party_overview") or []:
        if card.get("slot_id") == slot_id:
            return str(card.get("scene_name") or "").strip() or "???"
    return "???"


def choose_actor_slot(campaign: Dict[str, Any]) -> str:
    slots = campaign.get("available_slots") or []
    if not slots:
        raise LongRunError("Keine Slots in der Kampagne gefunden.")
    return slots[0]["slot_id"]


def sheet_payload(sheet: Dict[str, Any]) -> Dict[str, Any]:
    payload = sheet.get("sheet")
    return payload if isinstance(payload, dict) else {}


def sheet_skills(sheet: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = sheet_payload(sheet).get("skills")
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, dict)]
    if isinstance(raw, dict):
        entries = raw.get("entries")
        if isinstance(entries, list):
            return [entry for entry in entries if isinstance(entry, dict)]
    return []


def sheet_class_current(sheet: Dict[str, Any]) -> Dict[str, Any]:
    raw = sheet_payload(sheet).get("class")
    if isinstance(raw, dict):
        current = raw.get("current")
        if isinstance(current, dict):
            return current
    return {}


def active_skill_names(sheet: Dict[str, Any]) -> List[str]:
    skills = sheet_skills(sheet)
    return [str(entry.get("name") or "").strip() for entry in skills if str(entry.get("name") or "").strip()]


def state_flags(campaign: Dict[str, Any], sheet: Dict[str, Any], slot_id: str) -> Dict[str, Any]:
    char = (((campaign.get("state") or {}).get("characters") or {}).get(slot_id)) or {}
    class_current = sheet_class_current(sheet)
    plotpoints = ((campaign.get("state") or {}).get("plotpoints")) or []
    return {
        "hp_current": int(char.get("hp_current", 0) or 0),
        "hp_max": int(char.get("hp_max", 0) or 0),
        "sta_current": int(char.get("sta_current", 0) or 0),
        "sta_max": int(char.get("sta_max", 0) or 0),
        "res_current": int(char.get("res_current", 0) or 0),
        "res_max": int(char.get("res_max", 0) or 0),
        "injuries": len(char.get("injuries") or []),
        "scars": len(char.get("scars") or []),
        "conditions": len(char.get("conditions") or []),
        "inventory": len(char.get("inventory") or []),
        "class_name": str(class_current.get("name") or "").strip(),
        "skills": active_skill_names(sheet),
        "plotpoints": len(plotpoints),
    }


def request_signature(request: Dict[str, Any]) -> str:
    req_type = str(request.get("type") or "").strip().lower()
    question = str(request.get("question") or "").strip().lower()
    raw_options = request.get("options") or []
    options: List[str] = []
    for opt in raw_options:
        if isinstance(opt, dict):
            text = str(opt.get("text") or "").strip().lower()
        else:
            text = str(opt).strip().lower()
        if text:
            options.append(text)
    return f"{req_type}|{question}|{'||'.join(options)}"


def has_relic_learning_hook(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    return any(
        cue in normalized
        for cue in (
            "runen",
            "rune",
            "buch",
            "kiste",
            "relikt",
            "symbol",
            "glyph",
            "glyphen",
            "truhe",
            "artefakt",
        )
    )


def has_training_hook(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    return any(
        cue in normalized
        for cue in (
            "train",
            "technik",
            "haltung",
            "drill",
            "runenkörper",
            "rittertechnik",
            "eisen",
            "klingenführung",
            "schild",
            "prüfung",
            "aufstieg",
            "eid",
            "ordens",
            "schwur",
        )
    )


def answer_request(request: Dict[str, Any], observed: Dict[str, Any], rng: random.Random) -> Tuple[str, str]:
    req_type = str(request.get("type") or "").strip().lower()
    question = str(request.get("question") or "").strip()
    raw_options = request.get("options") or []
    options: List[str] = []
    for opt in raw_options:
        if isinstance(opt, dict):
            text = str(opt.get("text") or "").strip()
            if text:
                options.append(text)
        else:
            text = str(opt).strip()
            if text:
                options.append(text)
    signature = request_signature(request)
    if signature == observed.get("last_request_signature"):
        observed["request_repeats"] = int(observed.get("request_repeats", 0) or 0) + 1
    else:
        observed["last_request_signature"] = signature
        observed["request_repeats"] = 1
    if req_type == "choice" and options:
        option_counts = observed.setdefault("request_option_counts", {})
        signature_counts = option_counts.setdefault(signature, {})
        sorted_options = sorted(
            options,
            key=lambda option: (
                int(signature_counts.get(option, 0)),
                0 if option != observed.get("last_choice_text") else 1,
                option,
            ),
        )
        picked = sorted_options[0]
        repeats = int(observed.get("request_repeats", 0) or 0)
        if repeats >= 2 and len(set(options)) >= 2:
            remaining = [option for option in sorted_options if option != observed.get("last_choice_text")]
            if remaining:
                picked = remaining[0]
        if repeats >= 3:
            return "TUN", "Matchek bricht die Pattsituation auf und handelt sofort entschlossen, statt weiter dieselben Möglichkeiten nur abzuwägen."
        signature_counts[picked] = int(signature_counts.get(picked, 0)) + 1
        observed["last_choice_text"] = picked
        return "STORY", f"Matchek entscheidet sich bewusst für: {picked}."
    if req_type == "clarify":
        if "ziel" in question.lower():
            return "STORY", "Matchek priorisiert Überleben, Orientierung und die Suche nach einer sicheren magischen Spur."
        if "wie" in question.lower():
            return "STORY", "Matchek geht vorsichtig, kontrolliert und mit Blick auf verborgene Gefahren vor."
        return "STORY", f"Matchek beantwortet die offene Frage klar: {question} Er will einen riskanten, aber kontrollierten Fortschritt."
    return "STORY", CONTINUE_STORY_MARKER


def choose_turn_action(
    *,
    campaign: Dict[str, Any],
    sheet: Dict[str, Any],
    slot_id: str,
    turn_index: int,
    observed: Dict[str, bool],
    rng: random.Random,
    profile: str,
) -> Tuple[str, str]:
    last = latest_turn(campaign) or {}
    last_story = str(last.get("gm_text_display") or "").strip()
    requests = [req for req in (last.get("requests") or []) if str(req.get("type") or "").strip().lower() in {"clarify", "choice"}]
    flags = state_flags(campaign, sheet, slot_id)
    scene = pick_scene_name(campaign, slot_id)
    res_name = resource_label(campaign)
    class_name = flags["class_name"]
    skills = flags["skills"]
    skill_entries = sheet_skills(sheet)
    maxed_skill_entries = [
        entry
        for entry in skill_entries
        if int(entry.get("level", 0) or 0) >= max(int(entry.get("level_max", 10) or 10), 1)
    ]
    active_plotpoints = [
        entry
        for entry in (((campaign.get("state") or {}).get("plotpoints")) or [])
        if isinstance(entry, dict) and str(entry.get("status") or "active").strip().lower() == "active"
    ]
    has_class_ascension = any(str(entry.get("type") or "").strip().lower() == "class_ascension" for entry in active_plotpoints)
    if profile == "knight" and len(skills) == 1 and has_training_hook(last_story):
        learned = skills[0]
        focused_followups = [
            f"Matchek setzt {learned} sofort praktisch ein und zwingt die Technik unter Druck in eine zweite Form, aus der eine ergänzende Ritterkunst entstehen kann.",
            f"Matchek benutzt {learned} nicht nur defensiv, sondern versucht daraus eine zweite Technik für Vorstoß, Schild oder Standfestigkeit zu entwickeln.",
            f"Matchek trainiert {learned} weiter, aber diesmal gezielt mit Klinge, Haltung und Bewegung, bis daraus eine zweite benennbare Rittertechnik erwächst.",
        ]
        return "TUN", rng.choice(focused_followups)
    if profile == "knight" and len(skills) == 1 and turn_index >= 40 and requests:
        loop_break_actions = [
            f"Matchek ignoriert das Zögern der Szene und trainiert {skills[0]} aktiv weiter, bis aus Druck, Stahl und Haltung eine zweite Technik erzwungen wird.",
            f"Matchek nutzt die Pattsituation nicht zum Grübeln, sondern verwandelt sie in Drill: {skills[0]} soll unter echter Belastung eine ergänzende Ritterkunst hervorbringen.",
            f"Matchek bricht aus der Untersuchungsschleife aus und zwingt {skills[0]} in Bewegung, Schildarbeit und Vorstoß, bis eine zweite Technik entsteht oder klar scheitert.",
        ]
        return "TUN", rng.choice(loop_break_actions)
    if profile == "knight" and len(skills) >= 2 and turn_index >= 50 and requests and not has_class_ascension:
        ascension_force_actions = [
            "Matchek lässt die Kleinfragen der Szene hinter sich und sucht bewusst nach Eid, Reliquie oder Schwelle, die seinen Klassenaufstieg als Eisenritter erzwingen könnte.",
            "Matchek behandelt die Lage jetzt als Ritterprüfung und drängt aktiv auf den Auslöser einer höheren Klasse statt weiter bloß die Umgebung zu untersuchen.",
        ]
        return "STORY", rng.choice(ascension_force_actions)
    if profile == "knight" and len(skills) >= 2 and not has_class_ascension and has_training_hook(last_story):
        ascension_push = [
            "Matchek deutet seine gewachsenen Techniken als Zeichen einer kommenden Ritterprüfung und sucht jetzt bewusst nach Eid, Reliquie oder Schwelle für seinen Klassenaufstieg.",
            "Matchek behandelt die Lage nicht mehr als bloßes Überleben, sondern als Prüfung seines Ritterpfades und sucht aktiv nach dem Auslöser einer höheren Klasse.",
        ]
        return "STORY", rng.choice(ascension_push)
    if profile == "knight" and not skills and has_relic_learning_hook(last_story):
        relic_skill_actions = [
            "Matchek legt Buch und Kiste nebeneinander, vergleicht jede Rune mit seiner Haltung und zwingt sich in einen disziplinierten Drill, bis aus dem Reliktpfad eine erste benennbare Rittertechnik entsteht.",
            "Matchek versucht, die Runen nicht magisch, sondern als Kampflehre zu lesen: Atem, Stand, Winkel und eiserne Disziplin, bis daraus eine erste Technik wie Atem-Fokus oder Schildschritt hervorgeht.",
            "Matchek nutzt Buch, Kiste und Zeichen bewusst als Lehrmeister und trainiert so lange daran, bis die Relikte ihm eine erste echte Rittertechnik oder einen klaren Hinweis auf seinen Klassenweg offenbaren.",
        ]
        return "TUN", rng.choice(relic_skill_actions)

    if requests:
        observed["requests_seen"] = True
        return answer_request(requests[0], observed, rng)

    if turn_index > 0 and turn_index % 7 == 0:
        return "STORY", CONTINUE_STORY_MARKER

    if not observed["used_sagen"] and turn_index >= 5:
        return "SAGEN", "Matchek spricht laut in die Dunkelheit und fordert jeden Verbündeten oder Beobachter auf, sich zu zeigen, statt aus dem Schatten heraus zu spielen."

    if not observed["used_story"] and turn_index >= 3:
        if profile == "knight":
            return "STORY", "Matchek spürt, dass ihn weniger rohe Magie als eiserne Disziplin, Pflichtgefühl und der Wille zum Schutz anderer durch diese Welt tragen."
        return "STORY", "Matchek spürt, dass die Magie dieser Welt wie Mana unter seiner Haut kreist und ihn unruhig weiterzieht."

    if profile != "knight" and not observed["used_canon"] and turn_index >= 18:
        if skills:
            chosen_skill = rng.choice(skills)
            return "CANON", f"Matchek beherrscht {chosen_skill} inzwischen als festen Teil seines Repertoires."
        if class_name:
            title = f"{class_name} von {scene}" if scene != "???" else f"{class_name} im Grenzland"
            return "CANON", f"Matchek führt inzwischen den Beinamen {title}."

    if not class_name and turn_index >= 12:
        if profile == "knight":
            return "STORY", "Im Druck der Reise zeichnet sich in Matchek eine erste wahre Klasse ab, geboren aus Disziplin, Stahl und dem Willen, in vorderster Reihe standzuhalten."
        return "STORY", "Im Druck der Reise zeichnet sich in Matchek eine erste wahre Klasse ab, die aus Überleben, Kampfwille und dunkler Magie geboren wird."

    if not skills and turn_index >= 14:
        if profile == "knight":
            return "TUN", "Matchek trainiert Haltung, Schrittfolge und Klingenführung, bis aus bloßer Härte eine erste echte Rittertechnik entstehen könnte."
        return "TUN", f"Matchek meditiert im Schutz der Ruinen und versucht bewusst, das Mana dieser Welt in eine erste beherrschbare Technik zu formen."

    if profile == "knight":
        if not skills and turn_index >= 10:
            knight_first_skill_actions = [
                "Matchek zwingt sich in einen harten Drill aus Haltung, Atem und Klingenführung, bis aus eiserner Disziplin eine erste Technik wie Eisenhaltung oder Schildschritt entstehen könnte.",
                "Matchek trainiert defensiv gegen Wand und Stein, bis aus seiner Standfestigkeit eine echte Technik wie Schildwall oder Eisenkern hervorgehen könnte.",
                "Matchek wiederholt denselben Vorstoß mit Messer und freiem Arm, bis daraus eine benennbare Rittertechnik wächst statt bloßer roher Gewalt.",
            ]
            return "TUN", rng.choice(knight_first_skill_actions)
        if len(skills) == 1 and turn_index >= 18:
            learned = skills[0]
            knight_second_skill_actions = [
                f"Matchek baut auf {learned} auf und versucht nun bewusst eine zweite Kerntechnik zu entwickeln, die entweder seine Verteidigung oder seinen Durchbruch ergänzt.",
                f"Matchek trainiert {learned} nicht isoliert weiter, sondern sucht eine zweite Technik, die mit Disziplin, Stahl und Frontkampf sauber zusammenspielt.",
                f"Matchek versucht, aus dem Fundament von {learned} eine ergänzende Ritterkunst zu formen - etwas für Schild, Vorstoß oder eiserne Haltung.",
            ]
            return "TUN", rng.choice(knight_second_skill_actions)
        if len(skills) >= 2 and not has_class_ascension and turn_index >= 26:
            ascension_seek_actions = [
                "Matchek sucht bewusst nach einem Eid, Relikt oder Prüfstein, der seinen Weg als Eisenritter vertiefen und eine wahre Aufstiegsprüfung auslösen könnte.",
                "Matchek versucht, in den Zeichen dieser Welt eine Ritterprüfung zu finden - etwas, das ihn nicht nur stärker, sondern würdig für einen Klassenaufstieg macht.",
                "Matchek achtet gezielt auf Hinweise eines Ordens, Schwurs oder uralten Prüfpfades, der seinen Eisenritter-Weg in eine höhere Klasse führen könnte.",
            ]
            return "STORY", rng.choice(ascension_seek_actions)
        if len(skills) >= 2 and len(maxed_skill_entries) < 2 and turn_index >= 32:
            names = [str(entry.get("name") or "").strip() for entry in skill_entries[:2] if str(entry.get("name") or "").strip()]
            if len(names) >= 2:
                return "TUN", f"Matchek trainiert {names[0]} und {names[1]} bewusst zusammen, bis sich zeigt, ob beide Techniken sich gegenseitig steigern oder irgendwann zu etwas Neuem verschmelzen können."
            return "TUN", "Matchek trainiert zwei seiner wichtigsten Rittertechniken gezielt zusammen, um ihre Grenzen zu erreichen und eine spätere Verschmelzung vorzubereiten."
        if len(maxed_skill_entries) >= 2 and turn_index >= 40:
            names = [str(entry.get('name') or '').strip() for entry in maxed_skill_entries[:2] if str(entry.get('name') or '').strip()]
            if len(names) >= 2:
                return "TUN", f"Matchek führt {names[0]} und {names[1]} bis an ihre Grenze zusammen aus und versucht, ob daraus eine Evolution oder verschmolzene Ritterkunst hervorgeht."
            return "TUN", "Matchek presst zwei voll ausgereifte Techniken gegeneinander, um eine Evolution oder Verschmelzung zu erzwingen, wenn die Welt es zulässt."

    hp_ratio = flags["hp_current"] / max(flags["hp_max"], 1)
    sta_ratio = flags["sta_current"] / max(flags["sta_max"], 1)
    res_ratio = flags["res_current"] / max(flags["res_max"], 1)
    if flags["injuries"] or hp_ratio < 0.45 or sta_ratio < 0.35:
        return "TUN", "Matchek zieht sich in Deckung zurück, versorgt seine Verletzungen, ordnet seine Gedanken und sucht einen Moment echter Ruhe, ohne die Umgebung aus den Augen zu verlieren."

    if res_ratio < 0.3:
        return "TUN", f"Matchek sucht nach einer sicheren Methode, sein {res_name} wieder zu sammeln, ohne sich blind in ein neues Risiko zu werfen."

    exploration_actions = [
        f"Matchek erkundet {scene} vorsichtig weiter, sucht verwertbare Spuren, Kartenhinweise oder einen Weg tiefer in das Gebiet.",
        "Matchek untersucht die Architektur, Schriften und Symbole der Umgebung, um Ursprung, Bedrohung und mögliche verborgene Pfade zu verstehen.",
        "Matchek folgt den frischesten Spuren, aber nur so weit, dass er noch rechtzeitig auf eine Falle oder einen Hinterhalt reagieren kann.",
        "Matchek prüft die Ränder der Szene auf Eingänge, geheime Durchgänge, Lagerplätze oder Zeichen menschlicher Präsenz.",
    ]
    combat_actions = [
        "Matchek testet seine aktuelle Kampfkraft an der nächsten Bedrohung kontrolliert und versucht, die Schwäche des Gegners zuerst zu lesen, bevor er voll angreift.",
        "Matchek geht auf Distanz, erzwingt einen Fehler beim Gegner und nutzt dann die Lücke für einen harten, konzentrierten Schlag.",
        "Matchek versucht, Monster und Gelände gegeneinander auszuspielen, statt nur rohe Gewalt einzusetzen.",
    ]
    social_actions = [
        "Matchek versucht, mit jedem Fremden zuerst Informationen zu handeln, statt sofort Gewalt oder Drohung zu wählen.",
        "Matchek spricht einen möglichen Wachposten, Händler oder Reisenden direkt an und tastet seine Loyalität und Angstpunkte ab.",
    ]
    study_actions = [
        f"Matchek analysiert seine vorhandenen Skills und überlegt, welche Technik mit {res_name} am natürlichsten weiterentwickelt werden könnte.",
        "Matchek trainiert bewusst an einer vorhandenen Fähigkeit, bis aus roher Nutzung ein klarer Fortschritt oder eine neue Abwandlung wird.",
        "Matchek verbindet Kampf, Beobachtung und Magieübungen, um aus Erfahrung statt aus bloßer Hoffnung stärker zu werden.",
    ]
    if profile == "knight":
        combat_actions = [
            "Matchek geht mit kontrollierter Schild- und Klingenarbeit vor, zwingt den Gegner in einen Fehler und antwortet dann mit einem harten Vorstoß.",
            "Matchek hält die Linie, testet Reichweite und Timing des Gegners und sucht den Moment für einen entschlossenen Hieb aus der Deckung.",
            "Matchek nutzt Mauerwerk, Engstellen und Haltung, um wie ein disziplinierter Frontkämpfer standzuhalten statt blind zu stürmen.",
        ]
        study_actions = [
            "Matchek trainiert Schrittfolge, Haltung und Klingenwinkel, bis aus bloßer Zähigkeit eine echte Rittertechnik werden könnte.",
            "Matchek übt, Angriffe sauber mit Haltung und eiserner Disziplin abzufangen, um daraus eine defensive Kerntechnik zu formen.",
            "Matchek verbindet Kampfdrill, Wachsamkeit und Pflichtgefühl, um aus Erfahrung eine tragfähige Kriegerkunst aufzubauen.",
        ]

    bucket = rng.random()
    if turn_index % 9 == 0 and skills:
        return "TUN", rng.choice(study_actions)
    if bucket < 0.5:
        return "TUN", rng.choice(exploration_actions)
    if bucket < 0.78:
        return "TUN", rng.choice(combat_actions)
    if bucket < 0.9:
        return "SAGEN", rng.choice(social_actions)
    return "STORY", rng.choice(
        [
            "Matchek merkt, dass sich die Lage um ihn herum zuspitzt und jede Entscheidung jetzt länger nachhallen wird als zuvor.",
            "Matchek erkennt in den jüngsten Ereignissen ein Muster, das auf etwas Größeres hindeutet als einen isolierten Zwischenfall.",
            "Matchek spürt, dass sein Weg ihn tiefer in die dunkle Struktur dieser Welt zieht, statt ihn nur an ihrer Oberfläche entlangzuführen.",
        ]
    )


def write_log(log_path: Path, entry: Dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_long_campaign(
    turns: int,
    seed: int,
    *,
    smoke_only: bool = False,
    resume_campaign_id: Optional[str] = None,
    resume_player_id: Optional[str] = None,
    resume_player_token: Optional[str] = None,
    resume_slot_id: Optional[str] = None,
    profile: str = DEFAULT_PROFILE,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    if resume_campaign_id:
        campaign_id = resume_campaign_id
        player_id = str(resume_player_id or "")
        player_token = str(resume_player_token or "")
        if not player_id or not player_token:
            meta = load_session_meta(campaign_id)
            player_id = meta["player_id"]
            player_token = meta["player_token"]
        headers = viewer_headers(player_id, player_token)
        campaign = api("GET", f"/api/campaigns/{campaign_id}", headers=headers)
        slot_id = resume_slot_id or choose_actor_slot(campaign)
    else:
        created = api("POST", "/api/campaigns", body={"title": f"Automatikrun {utc_timestamp()}", "display_name": "Codex"})
        campaign_id = created["campaign_id"]
        player_id = created["player_id"]
        player_token = created["player_token"]
        headers = viewer_headers(player_id, player_token)
        save_session_meta(
            {
                "campaign_id": campaign_id,
                "player_id": player_id,
                "player_token": player_token,
            }
        )
        log_path = latest_run_log_for_campaign(campaign_id)
        write_log(log_path, {"step": "campaign_created", "campaign_id": campaign_id})

        world_preview = api(
            "POST",
            f"/api/campaigns/{campaign_id}/setup/world/random",
            headers=headers,
            body={"mode": "all", "preview_answers": []},
        )
        world_apply = api(
            "POST",
            f"/api/campaigns/{campaign_id}/setup/world/random/apply",
            headers=headers,
            body={"mode": "all", "preview_answers": mutate_world_preview(world_preview["preview_answers"])},
        )
        patch_world_resource_name(campaign_id, "Mana")

        slot_id = choose_actor_slot(world_apply["campaign"])
        api("POST", f"/api/campaigns/{campaign_id}/slots/{slot_id}/claim", headers=headers)

        campaign = None
        for _ in range(6):
            char_preview = api(
                "POST",
                f"/api/campaigns/{campaign_id}/slots/{slot_id}/setup/random",
                headers=headers,
                body={"mode": "all", "preview_answers": []},
            )
            char_apply = api(
                "POST",
                f"/api/campaigns/{campaign_id}/slots/{slot_id}/setup/random/apply",
                headers=headers,
                body={"mode": "all", "preview_answers": mutate_character_preview(char_preview["preview_answers"], profile)},
            )
            campaign = char_apply["campaign"]
            if char_apply.get("completed"):
                break
        if not campaign:
            raise LongRunError("Der Charakterlauf konnte nicht initialisiert werden.")
        if not char_apply.get("completed"):
            raise LongRunError("Das Charakter-Setup wurde nicht vollständig abgeschlossen.")
        if (campaign.get("state") or {}).get("meta", {}).get("phase") != "adventure":
            intro_payload = api(
                "POST",
                f"/api/campaigns/{campaign_id}/intro/retry",
                headers=headers,
            )
            campaign = intro_payload.get("campaign") or api("GET", f"/api/campaigns/{campaign_id}", headers=headers)
        if (campaign.get("state") or {}).get("meta", {}).get("phase") != "adventure":
            raise LongRunError("Der Lauf hat die Adventure-Phase nicht erreicht.")

    observed = {
        "used_story": False,
        "used_sagen": False,
        "used_canon": False,
        "requests_seen": False,
    }
    failures = 0
    total_turns = 0
    log_path = latest_run_log_for_campaign(campaign_id)
    already_done = len((load_json(campaign_file(campaign_id)).get("turns") or []))

    while total_turns + already_done < turns:
        turn_index = total_turns + already_done
        campaign = api("GET", f"/api/campaigns/{campaign_id}", headers=headers)
        sheet = api("GET", f"/api/campaigns/{campaign_id}/characters/{slot_id}", headers=headers)
        mode, text = choose_turn_action(
            campaign=campaign,
            sheet=sheet,
            slot_id=slot_id,
            turn_index=turn_index,
            observed=observed,
            rng=rng,
            profile=profile,
        )
        if mode == "STORY" and text == CONTINUE_STORY_MARKER:
            display_text = "Weiter"
        else:
            display_text = text
        try:
            result = api(
                "POST",
                f"/api/campaigns/{campaign_id}/turns",
                headers=headers,
                body={"actor": slot_id, "mode": mode, "text": text},
                timeout=600,
            )
            campaign = result["campaign"]
            last = latest_turn(campaign) or {}
            total_turns += 1
            failures = 0
            observed["used_story"] = observed["used_story"] or mode == "STORY"
            observed["used_sagen"] = observed["used_sagen"] or mode == "SAGEN"
            observed["used_canon"] = observed["used_canon"] or mode == "CANON"
            write_log(
                log_path,
                {
                    "step": "turn_ok",
                    "index": turn_index + 1,
                    "mode": mode,
                    "input": display_text,
                    "turn_id": last.get("turn_id"),
                    "turn_number": last.get("turn_number"),
                    "requests": last.get("requests") or [],
                    "gm_excerpt": str(last.get("gm_text_display") or "")[:1000],
                    "scene": pick_scene_name(campaign, slot_id),
                    "class_name": sheet_class_current(sheet).get("name"),
                    "skills": active_skill_names(sheet),
                },
            )
        except Exception as exc:
            failures += 1
            write_log(
                log_path,
                {
                    "step": "turn_error",
                    "index": turn_index + 1,
                    "mode": mode,
                    "input": display_text,
                    "error": str(exc),
                },
            )
            if failures >= 6:
                raise
            time.sleep(min(10, failures * 2))
            continue
        if smoke_only and total_turns >= turns:
            break
        time.sleep(0.4)

    final_campaign = api("GET", f"/api/campaigns/{campaign_id}", headers=headers)
    export_path = RUN_OUTPUT_DIR / f"{campaign_id}_export.json"
    export_path.write_text(json.dumps(api("GET", f"/api/campaigns/{campaign_id}/export", headers=headers), ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "campaign_id": campaign_id,
        "player_id": player_id,
        "player_token": player_token,
        "slot_id": slot_id,
        "turns_completed": len((load_json(campaign_file(campaign_id)).get("turns") or [])),
        "log_path": str(log_path),
        "export_path": str(export_path),
        "resource_name": resource_label(final_campaign),
        "scene": pick_scene_name(final_campaign, slot_id),
        "observed": observed,
    }
    write_log(log_path, {"step": "finished", **summary})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Organischer Langlauf für Aelunor")
    parser.add_argument("--turns", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260304)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--campaign-id")
    parser.add_argument("--player-id")
    parser.add_argument("--player-token")
    parser.add_argument("--slot-id")
    args = parser.parse_args()
    summary = run_long_campaign(
        args.turns,
        args.seed,
        smoke_only=args.smoke,
        resume_campaign_id=args.campaign_id,
        resume_player_id=args.player_id,
        resume_player_token=args.player_token,
        resume_slot_id=args.slot_id,
        profile=args.profile,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

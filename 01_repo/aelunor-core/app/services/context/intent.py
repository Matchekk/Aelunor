import json
import re
from typing import Any, Dict

from app.core.ids import hash_secret
from app.services.world.text_normalization import normalized_eval_text


def context_state_signature(state: Dict[str, Any]) -> str:
    serialized = json.dumps(state or {}, ensure_ascii=False, sort_keys=True, default=str)
    return hash_secret(serialized)


def strip_markdown_like(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"^\s*#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    cleaned = re.sub(r"^\s*[-*]\s+", "\u2022 ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def parse_context_intent(question: str) -> Dict[str, str]:
    raw = str(question or "").strip()
    lowered = normalized_eval_text(raw)
    target = ""
    intent = "unknown"
    patterns = [
        ("define", r"(?:^|\b)(?:was ist|was bedeutet|erklaer mir|erkl\u00e4r mir|was ist nochmal)\s+(.+)$"),
        ("who", r"(?:^|\b)(?:wer ist|wer war)\s+(.+)$"),
        ("where", r"(?:^|\b)(?:wo ist|wo befindet sich|wo liegt)\s+(.+)$"),
    ]
    for detected_intent, pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            intent = detected_intent
            target = match.group(1)
            break
    if not target:
        quoted = re.search(r"[\"\u201c\u201e']([^\"\u201c\u201d\u201e']{2,120})[\"\u201d\u201e']", raw)
        if quoted:
            target = quoted.group(1)
            if intent == "unknown":
                intent = "define"
    if intent == "unknown":
        if any(marker in lowered for marker in ("zusammenfassung", "aktueller stand", "was bisher", "worum geht")):
            intent = "summary"
        elif any(marker in lowered for marker in ("vergleich", "unterschied", "vs ", "gegen\u00fcber")):
            intent = "compare"
    target = re.sub(r"\?$", "", str(target or "").strip()).strip(" .,:;!?")
    target = re.sub(r"^(?:ein(?:e|en|em|er)?|der|die|das)\s+", "", target, flags=re.IGNORECASE).strip()
    return {"intent": intent, "target": target}

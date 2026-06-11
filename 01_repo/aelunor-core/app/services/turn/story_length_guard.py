import json
import re
from typing import Any, Callable, Dict, List, Optional, Type


_STRUCTURAL_STORY_LEAK_MARKERS = (
    '", "patch"',
    '", "requests"',
    '\\"patch\\"',
    '\\"requests\\"',
    "\nPATCH",
    "\nREQUESTS",
    "\nOUTPUT-KONTRAKT",
    "\nPLAYER_ACTION",
    "\nCONTEXT_PACKET",
    "\n*Anmerkung",
    "\n---",
    "\n**Update",
    "\nUpdate für dich",
)
_MODEL_COMMENTARY_MARKERS = (
    "the core issue is",
    "i will now",
    "let me re-read",
    "okay, let's go",
    "the prompt asks me",
    "wait, tell me",
    "anmerkung:",
    "update für dich",
)


def _strip_story_leaks(story: str) -> str:
    content = str(story or "").strip()
    if not content:
        return ""
    candidates = []
    for marker in _STRUCTURAL_STORY_LEAK_MARKERS:
        index = content.find(marker)
        if index >= 0:
            candidates.append(index)
    lowered = content.lower()
    for marker in _MODEL_COMMENTARY_MARKERS:
        index = lowered.find(marker)
        if index >= 0:
            candidates.append(index)
    match = re.search(r"(?:_[a-z0-9]){16,}", content, flags=re.IGNORECASE)
    if match:
        candidates.append(match.start())
    structural_tail = re.search(
        r'["\']?\s*,?\s*\r?\n\s*(?:\\?")?(?:patch|requests)(?:\\?")?\s*:',
        content,
        flags=re.IGNORECASE,
    )
    if structural_tail:
        candidates.append(structural_tail.start())
    if candidates:
        content = content[: min(candidates)]
    return re.sub(r"\n{3,}", "\n\n", content).strip(" \n\r\t,;")


def _trim_story_to_max(story: str, max_story_chars: int) -> str:
    content = str(story or "").strip()
    if max_story_chars <= 0 or len(content) <= max_story_chars:
        return content
    window = content[: max_story_chars + 1]
    sentence_end = max(window.rfind("."), window.rfind("!"), window.rfind("?"))
    if sentence_end >= max(120, max_story_chars // 2):
        return window[: sentence_end + 1].strip()
    return window[:max_story_chars].rstrip(" ,;:")


def rewrite_story_length_guard(
    *,
    system_prompt: str,
    user_prompt: str,
    story_text: str,
    patch: Dict[str, Any],
    requests_payload: List[Dict[str, Any]],
    min_story_chars: int,
    max_story_chars: int,
    min_story_rewrite_attempts: int,
    max_story_compress_attempts: int,
    story_rewrite_schema: Dict[str, Any],
    ollama_temperature: float,
    call_ollama_schema: Callable[..., Dict[str, Any]],
    http_exception_type: Type[Exception],
    ollama_timeout_sec: Optional[int] = None,
) -> str:
    raw_story = str(story_text or "").strip()
    story = _strip_story_leaks(raw_story)
    if not raw_story:
        return ""
    rewrite_timeout = max(120, int(ollama_timeout_sec or 120))
    compress_timeout = max(90, int(ollama_timeout_sec or 90))
    rewrite_instruction = (
        "REWRITE-AUFTRAG:\n"
        f"- Schreibe dieselbe Szene neu.\n"
        f"- story muss mindestens {min_story_chars} Zeichen enthalten.\n"
        "- Mehr Plotbewegung, weniger Fülltext.\n"
        "- Keine Wiederholung alter Absätze.\n"
        "- Bewahre exakt dieselben kanonischen Fakten bei.\n"
        "- Ändere keine Struktur außerhalb von story.\n"
    )
    for _ in range(min_story_rewrite_attempts):
        if len(story) >= min_story_chars:
            break
        rewrite_user = (
            user_prompt
            + "\n\n"
            + rewrite_instruction
            + "\nAktuelle zu kurze story:\n"
            + story
            + "\n\nPATCH (unverändert lassen):\n"
            + json.dumps(patch or {}, ensure_ascii=False)
            + "\nREQUESTS (unverändert lassen):\n"
            + json.dumps(requests_payload or [], ensure_ascii=False)
        )
        rewritten = call_ollama_schema(
            system_prompt,
            rewrite_user,
            story_rewrite_schema,
            timeout=rewrite_timeout,
            temperature=max(0.4, ollama_temperature - 0.05),
        )
        story = _strip_story_leaks(str((rewritten or {}).get("story", "") or "").strip())
    if len(story) < min_story_chars:
        raise http_exception_type(status_code=500, detail=f"Modell konnte Mindestlänge ({min_story_chars}) nach Retry nicht erfüllen. Bitte erneut versuchen.")

    for _ in range(max_story_compress_attempts):
        if len(story) <= max_story_chars:
            break
        compress_user = (
            user_prompt
            + "\n\nKOMPRIMIERUNGSAUFTRAG:\n"
            + f"- Kürze dieselbe Szene auf maximal {max_story_chars} Zeichen.\n"
            + "- Keine Fakten verlieren, keine Wiederholung, gleiche Konsequenzen.\n"
            + "\nAktuelle lange story:\n"
            + story
        )
        compressed = call_ollama_schema(
            system_prompt,
            compress_user,
            story_rewrite_schema,
            timeout=compress_timeout,
            temperature=max(0.35, ollama_temperature - 0.1),
        )
        story = _strip_story_leaks(str((compressed or {}).get("story", "") or "").strip())
    story = _trim_story_to_max(story, max_story_chars)
    if len(story) < min_story_chars:
        raise http_exception_type(status_code=500, detail=f"Modell konnte Mindestlänge ({min_story_chars}) nach Komprimierung nicht erfüllen. Bitte erneut versuchen.")
    return story

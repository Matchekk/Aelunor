import json
from typing import Any, Callable, Dict, List, Optional, Type


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
    story = str(story_text or "").strip()
    if not story:
        return story
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
        story = str((rewritten or {}).get("story", "") or "").strip()
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
        story = str((compressed or {}).get("story", "") or "").strip()
    return story

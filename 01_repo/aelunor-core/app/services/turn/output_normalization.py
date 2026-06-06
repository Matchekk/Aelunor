"""Normalize raw model turn output into the canonical story/patch/requests shape.

Pure turn-domain logic extracted from the state runtime core.
"""
from typing import Any, Dict, List, Optional

from app.services.patch_payloads import normalize_patch_payload
from app.services.world.text_normalization import normalized_eval_text


def normalize_request_option_text(option: Any) -> str:
    if isinstance(option, dict):
        for key in ("text", "label", "value", "name", "title"):
            value = option.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""
    if option is None:
        return ""
    if isinstance(option, (list, tuple, set)):
        return ""
    return str(option).strip()


def normalize_request_entry(entry: Any, *, default_actor: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(entry, dict):
        return None
    request_type = str(entry.get("type") or "").strip().lower()
    question = str(entry.get("question") or entry.get("prompt") or "").strip()
    raw_options = entry.get("options")
    if raw_options is None:
        raw_options = entry.get("choices")
    if isinstance(raw_options, dict):
        raw_options = list(raw_options.values())
    elif raw_options is None:
        raw_options = []
    elif not isinstance(raw_options, list):
        raw_options = [raw_options]
    options: List[str] = []
    seen = set()
    for raw_option in raw_options:
        option_text = normalize_request_option_text(raw_option)
        normalized_option = normalized_eval_text(option_text)
        if not option_text or normalized_option in seen:
            continue
        seen.add(normalized_option)
        options.append(option_text)
    if request_type not in {"clarify", "choice", "none"}:
        if options:
            request_type = "choice"
        elif question:
            request_type = "clarify"
        else:
            request_type = "none"
    if request_type == "choice" and not options:
        request_type = "clarify" if question else "none"
    actor = str(entry.get("actor") or default_actor or "").strip()
    normalized_entry: Dict[str, Any] = {"type": request_type, "actor": actor}
    if request_type in {"clarify", "choice"} and question:
        normalized_entry["question"] = question
    if request_type == "choice" and options:
        normalized_entry["options"] = options
    return normalized_entry


def normalize_requests_payload(payload: Any, *, default_actor: str = "") -> List[Dict[str, Any]]:
    if payload is None:
        raw_entries: List[Any] = []
    elif isinstance(payload, dict):
        raw_entries = [payload]
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        raw_entries = []
    normalized_entries: List[Dict[str, Any]] = []
    for raw_entry in raw_entries:
        normalized_entry = normalize_request_entry(raw_entry, default_actor=default_actor)
        if normalized_entry:
            normalized_entries.append(normalized_entry)
    return normalized_entries


def normalize_model_output_payload(payload: Any, *, default_actor: str = "") -> Dict[str, Any]:
    candidate = payload
    if isinstance(candidate, dict):
        for wrapper_key in ("response", "result", "output", "content", "data"):
            wrapped = candidate.get(wrapper_key)
            if isinstance(wrapped, dict) and (
                "story" in wrapped
                or "patch" in wrapped
                or "requests" in wrapped
                or "gm_text" in wrapped
                or "text" in wrapped
            ):
                candidate = wrapped
                break
    if not isinstance(candidate, dict):
        return {}

    story = candidate.get("story")
    if not isinstance(story, str) or not story.strip():
        for fallback_key in ("gm_text", "text", "narration", "message"):
            fallback_story = candidate.get(fallback_key)
            if isinstance(fallback_story, str) and fallback_story.strip():
                story = fallback_story
                break

    patch = normalize_patch_payload(candidate.get("patch"))

    normalized = {
        "story": str(story or "").strip(),
        "patch": patch,
        "requests": normalize_requests_payload(candidate.get("requests"), default_actor=default_actor),
    }
    return normalized if normalized["story"] else {}

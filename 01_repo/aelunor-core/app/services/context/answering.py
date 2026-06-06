import json
from typing import Any, Callable, Dict, List, Optional

from app.adapters.ollama_config import (
    OLLAMA_ADAPTER,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT_SEC,
)
from app.config.errors import ERROR_CODE_JSON_REPAIR
from app.catalogs.runtime_catalogs import RESPONSE_SCHEMA
from app.prompts.system_prompts import CONTEXT_ASSISTANT_SYSTEM_PROMPT
from app.schemas.llm import CONTEXT_RESPONSE_SCHEMA
from app.services.context.intent import strip_markdown_like
from app.services.llm.client import build_default_llm_client_settings
from app.services.llm.client import call_ollama_schema as _call_ollama_schema
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import CONTEXT_META_DRIFT_MARKERS


def build_context_result_payload(
    *,
    status: str,
    intent: str,
    target: str,
    confidence: str,
    entity_type: str,
    entity_id: str,
    title: str,
    explanation: str,
    facts: Optional[List[str]] = None,
    sources: Optional[List[Dict[str, str]]] = None,
    suggestions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "status": status if status in {"found", "not_in_canon", "ambiguous"} else "not_in_canon",
        "intent": intent if intent in {"define", "who", "where", "summary", "compare", "unknown"} else "unknown",
        "target": str(target or "").strip(),
        "confidence": confidence if confidence in {"high", "medium", "low"} else "low",
        "entity_type": str(entity_type or "unknown"),
        "entity_id": str(entity_id or ""),
        "title": str(title or "").strip(),
        "explanation": strip_markdown_like(explanation),
        "facts": [strip_markdown_like(fact) for fact in (facts or []) if str(fact or "").strip()],
        "sources": [
            {
                "type": str(entry.get("type") or "").strip(),
                "id": str(entry.get("id") or "").strip(),
                "label": strip_markdown_like(str(entry.get("label") or "").strip()),
            }
            for entry in (sources or [])
            if isinstance(entry, dict) and str(entry.get("type") or "").strip() and str(entry.get("id") or "").strip()
        ],
        "suggestions": [strip_markdown_like(suggestion) for suggestion in (suggestions or []) if str(suggestion or "").strip()],
    }


def deterministic_context_result_from_entry(
    intent: str,
    target: str,
    entry: Dict[str, Any],
    confidence: str,
) -> Dict[str, Any]:
    title = str(entry.get("title") or target or "Kanon-Eintrag").strip()
    facts = [str(fact).strip() for fact in (entry.get("facts") or []) if str(fact).strip()]
    if intent == "where":
        explanation = (
            f"Im aktuellen Kanon ist \u201e{title}\u201c als relevanter Eintrag erfasst. "
            "Der letzte bekannte Ortsbezug steht in den gefundenen Fakten und Quellen."
        )
    elif intent == "who":
        explanation = (
            f"\u201e{title}\u201c ist im aktuellen Kanon als Figur oder Referenz vorhanden. "
            "Hier sind die best\u00e4tigten Eckdaten aus dem Zustand."
        )
    else:
        explanation = (
            f"Im aktuellen Kanon bedeutet \u201e{title}\u201c Folgendes. "
            "Die Antwort basiert auf den gespeicherten Zustandsdaten dieser Kampagne."
        )
    return build_context_result_payload(
        status="found",
        intent=intent,
        target=target,
        confidence=confidence,
        entity_type=str(entry.get("type") or "unknown"),
        entity_id=str(entry.get("id") or ""),
        title=title,
        explanation=explanation,
        facts=facts[:8],
        sources=entry.get("sources") or [],
        suggestions=[],
    )


def context_meta_drift_detected(result: Dict[str, Any]) -> bool:
    merged = normalized_eval_text(
        f"{result.get('title', '')}\n{result.get('explanation', '')}\n{' '.join(result.get('facts') or [])}"
    )
    return any(marker in merged for marker in CONTEXT_META_DRIFT_MARKERS)


def default_context_call_ollama_schema(
    system: str,
    user: str,
    schema: Dict[str, Any],
    *,
    timeout: Optional[int] = None,
    temperature: float = 0.45,
) -> Dict[str, Any]:
    settings = build_default_llm_client_settings(
        timeout_sec=OLLAMA_TIMEOUT_SEC,
        temperature=OLLAMA_TEMPERATURE,
        response_schema=RESPONSE_SCHEMA,
        error_code_json_repair=ERROR_CODE_JSON_REPAIR,
    )
    return _call_ollama_schema(
        OLLAMA_ADAPTER,
        settings,
        system,
        user,
        schema,
        timeout=timeout,
        temperature=temperature,
    )


def build_context_result_via_llm(
    question: str,
    intent: str,
    target: str,
    snippets: List[Dict[str, Any]],
    *,
    call_schema: Callable[..., Dict[str, Any]] = default_context_call_ollama_schema,
) -> Optional[Dict[str, Any]]:
    user_prompt = (
        "KONTEXTFRAGE:\n"
        + str(question or "")
        + "\n\nRETRIEVAL_SNIPPETS(JSON):\n"
        + json.dumps(snippets, ensure_ascii=False)
        + "\n\nANTWORTREGELN:\n"
        + "- Nutze ausschlie\u00dflich Fakten aus RETRIEVAL_SNIPPETS.\n"
        + "- Wenn nicht genug Informationen vorliegen, status=not_in_canon oder ambiguous.\n"
        + "- Kein Markdown, kein Meta \u00fcber Textanalyse."
    )
    try:
        payload = call_schema(
            CONTEXT_ASSISTANT_SYSTEM_PROMPT,
            user_prompt,
            CONTEXT_RESPONSE_SCHEMA,
            timeout=90,
            temperature=0.2,
        )
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    normalized_result = build_context_result_payload(
        status=str(payload.get("status") or "not_in_canon"),
        intent=str(payload.get("intent") or intent),
        target=str(payload.get("target") or target),
        confidence=str(payload.get("confidence") or "low"),
        entity_type=str(payload.get("entity_type") or "unknown"),
        entity_id=str(payload.get("entity_id") or ""),
        title=str(payload.get("title") or (target or "Kontext")),
        explanation=str(payload.get("explanation") or ""),
        facts=payload.get("facts") if isinstance(payload.get("facts"), list) else [],
        sources=payload.get("sources") if isinstance(payload.get("sources"), list) else [],
        suggestions=payload.get("suggestions") if isinstance(payload.get("suggestions"), list) else [],
    )
    if context_meta_drift_detected(normalized_result):
        return None
    return normalized_result


def context_result_to_answer_text(result: Dict[str, Any]) -> str:
    status = str(result.get("status") or "not_in_canon")
    title = str(result.get("title") or result.get("target") or "Kontext").strip() or "Kontext"
    explanation = strip_markdown_like(str(result.get("explanation") or "").strip())
    facts = [strip_markdown_like(str(entry or "").strip()) for entry in (result.get("facts") or []) if str(entry or "").strip()]
    suggestions = [strip_markdown_like(str(entry or "").strip()) for entry in (result.get("suggestions") or []) if str(entry or "").strip()]
    sources = [strip_markdown_like(str((entry or {}).get("label") or "").strip()) for entry in (result.get("sources") or []) if isinstance(entry, dict)]
    sources = [entry for entry in sources if entry]

    if status == "found":
        lines = [explanation or f"Im aktuellen Kanon ist \u201e{title}\u201c eindeutig hinterlegt."]
        if facts:
            lines.append("Fakten: " + "; ".join(facts[:6]))
        if sources:
            lines.append("Gefunden in: " + ", ".join(sources[:4]))
        return "\n\n".join(lines).strip()

    if status == "ambiguous":
        lines = [f"Der Begriff \u201e{title}\u201c ist mehrdeutig im aktuellen Kanon."]
        if suggestions:
            lines.append("Meintest du: " + ", ".join(suggestions[:6]))
        return "\n\n".join(lines).strip()

    lines = [f"Der Begriff \u201e{title}\u201c ist im aktuellen Kanon nicht hinterlegt."]
    if suggestions:
        lines.append("\u00c4hnliche Begriffe: " + ", ".join(suggestions[:6]))
    return "\n\n".join(lines).strip()

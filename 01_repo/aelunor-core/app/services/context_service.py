from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class ContextServiceDependencies:
    load_campaign: Callable[[str], CampaignState]
    authenticate_player: Callable[..., None]
    player_claim: Callable[[CampaignState, Optional[str]], Optional[str]]
    active_party: Callable[[CampaignState], Any]
    campaign_slots: Callable[[CampaignState], Any]
    context_state_signature: Callable[[Dict[str, Any]], str]
    parse_context_intent: Callable[[str], Dict[str, Any]]
    build_context_knowledge_index: Callable[[CampaignState, Dict[str, Any]], Dict[str, Any]]
    resolve_context_target: Callable[[Dict[str, Any], str], Dict[str, Any]]
    deterministic_context_result_from_entry: Callable[..., Dict[str, Any]]
    build_context_result_payload: Callable[..., Dict[str, Any]]
    extract_story_target_evidence: Callable[[CampaignState, str], Dict[str, Any]]
    build_reduced_context_snippets: Callable[..., Any]
    build_context_result_via_llm: Callable[..., Optional[Dict[str, Any]]]
    context_result_to_answer_text: Callable[[Dict[str, Any]], str]


def query_campaign_context(
    *,
    campaign_id: str,
    question: str,
    actor: Optional[str],
    player_id: Optional[str],
    player_token: Optional[str],
    deps: ContextServiceDependencies,
) -> Dict[str, Any]:
    campaign = deps.load_campaign(campaign_id)
    deps.authenticate_player(campaign, player_id, player_token, required=True)
    normalized_question = str(question or "").strip()
    if not normalized_question:
        raise HTTPException(status_code=400, detail="Leere Kontextfrage ist nicht erlaubt.")

    normalized_actor = str(actor or "").strip()
    if normalized_actor:
        if normalized_actor not in campaign.get("state", {}).get("characters", {}):
            raise HTTPException(status_code=400, detail="Unbekannter Slot für Kontextfrage.")
    else:
        normalized_actor = (
            deps.player_claim(campaign, player_id)
            or (deps.active_party(campaign)[0] if deps.active_party(campaign) else "")
            or (deps.campaign_slots(campaign)[0] if deps.campaign_slots(campaign) else "")
        )
    if not normalized_actor:
        raise HTTPException(status_code=409, detail="Kein verfügbarer Kontext-Actor vorhanden.")
    state = campaign["state"]
    signature_before = deps.context_state_signature(state)

    intent_data = deps.parse_context_intent(normalized_question)
    intent = str(intent_data.get("intent") or "unknown")
    target = str(intent_data.get("target") or "").strip()

    index = deps.build_context_knowledge_index(campaign, state)
    result: Optional[Dict[str, Any]] = None

    if target:
        resolved = deps.resolve_context_target(index, target)
        if resolved.get("status") == "found" and isinstance(resolved.get("entry"), dict):
            result = deps.deterministic_context_result_from_entry(
                intent=intent,
                target=target,
                entry=resolved["entry"],
                confidence=str(resolved.get("confidence") or "medium"),
            )
        elif resolved.get("status") == "ambiguous":
            suggestions = resolved.get("suggestions") if isinstance(resolved.get("suggestions"), list) else []
            result = deps.build_context_result_payload(
                status="ambiguous",
                intent=intent,
                target=target,
                confidence=str(resolved.get("confidence") or "low"),
                entity_type="unknown",
                entity_id="",
                title=target,
                explanation=f"Der Begriff „{target}“ ist im aktuellen Kanon mehrdeutig.",
                facts=[],
                sources=[],
                suggestions=suggestions[:8],
            )
        else:
            story_evidence = deps.extract_story_target_evidence(campaign, target, max_hits=5)
            story_facts = story_evidence.get("facts") if isinstance(story_evidence.get("facts"), list) else []
            story_sources = story_evidence.get("sources") if isinstance(story_evidence.get("sources"), list) else []
            if story_facts:
                result = deps.build_context_result_payload(
                    status="found",
                    intent=intent,
                    target=target,
                    confidence="medium",
                    entity_type="unknown",
                    entity_id="",
                    title=target,
                    explanation=(
                        f"Der Begriff „{target}“ ist nicht als eigener Codex-Eintrag hinterlegt, "
                        "kommt aber in der laufenden Geschichte vor."
                    ),
                    facts=story_facts[:5],
                    sources=story_sources[:5],
                    suggestions=[],
                )
            else:
                suggestions = resolved.get("suggestions") if isinstance(resolved.get("suggestions"), list) else []
                result = deps.build_context_result_payload(
                    status="not_in_canon",
                    intent=intent,
                    target=target,
                    confidence="low",
                    entity_type="unknown",
                    entity_id="",
                    title=target,
                    explanation=f"Der Begriff „{target}“ ist im aktuellen Kanon nicht hinterlegt.",
                    facts=[],
                    sources=[],
                    suggestions=suggestions[:8],
                )

    if result is None and intent in {"summary", "compare", "unknown"}:
        llm_target = target or normalized_question
        snippets = deps.build_reduced_context_snippets(index, target=llm_target, limit=14)
        llm_result = deps.build_context_result_via_llm(normalized_question, intent, llm_target, snippets)
        if llm_result is not None:
            result = llm_result
        else:
            result = deps.build_context_result_payload(
                status="not_in_canon",
                intent=intent,
                target=llm_target,
                confidence="low",
                entity_type="unknown",
                entity_id="",
                title=llm_target,
                explanation="Für diese Frage konnte ich im aktuellen Kanon keine belastbaren Fakten finden.",
                facts=[],
                sources=[],
                suggestions=[],
            )

    if result is None:
        fallback_target = target or normalized_question
        result = deps.build_context_result_payload(
            status="not_in_canon",
            intent=intent,
            target=fallback_target,
            confidence="low",
            entity_type="unknown",
            entity_id="",
            title=fallback_target,
            explanation=f"Der Begriff „{fallback_target}“ ist im aktuellen Kanon nicht hinterlegt.",
            facts=[],
            sources=[],
            suggestions=[],
        )

    answer = deps.context_result_to_answer_text(result)
    if not answer:
        answer = "Keine belastbare Kontextantwort verfügbar."

    signature_after = deps.context_state_signature(campaign["state"])
    if signature_before != signature_after:
        raise HTTPException(status_code=500, detail="Kontextabfrage hat unerwartet den Zustand verändert.")

    return {"answer": answer, "actor": normalized_actor, "question": normalized_question, "result": result}


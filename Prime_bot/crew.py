from classifier.intent_classifier import classify
from memory.session_memory import SessionMemory
import re
import time
import agents.router_agent as router_agent
import agents.product_advisor as product_advisor
import agents.cardholder_svc as cardholder_svc
import agents.comparator as comparator
import agents.compliance_faq as compliance_faq
import agents.synthesis_agent as synthesis_agent
import yaml
from logging_utils import log_event

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_eligibility_sessions: set[str] = set()


def _guardrails(response: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
    if not cleaned or len(cleaned) < 10:
        return (
            "I'm sorry, I couldn't find relevant information in my knowledge base for that query. "
            "Please contact Prime Bank directly at **16218** or visit any Prime Bank branch for assistance."
        )
    return cleaned


def _normalize_intent(intent: str) -> str:
    if intent in {
        "i_need_a_credit_card",
        "existing_cardholder",
        "comparison",
        "eligibility_check",
        "catalog_query",
        "faq_compliance",
    }:
        return intent
    return "faq_compliance"


def build_crew(user_message: str, session: SessionMemory, request_id: str | None = None) -> str:
    started = time.perf_counter()
    classifier_output = classify(user_message)
    session_id = session.session_id
    in_eligibility = session_id in _eligibility_sessions
    log_event(
        "classifier_result",
        request_id=request_id,
        session_id=session_id,
        intent=classifier_output.get("intent"),
        banking_type=classifier_output.get("banking_type"),
        intent_score=round(classifier_output.get("intent_score", 0.0), 4),
        banking_score=round(classifier_output.get("banking_score", 0.0), 4),
    )

    if in_eligibility and classifier_output["intent"] not in ("comparison", "catalog_query"):
        classifier_output["intent"] = "eligibility_check"

    routing = router_agent.run(user_message, classifier_output, session)
    intent = _normalize_intent(routing.get("intent", classifier_output["intent"]))
    routing["intent"] = intent
    log_event(
        "route_selected",
        request_id=request_id,
        session_id=session_id,
        intent=intent,
        banking_type=routing.get("banking_type"),
        collection=routing.get("collection"),
    )

    if intent == "comparison":
        _eligibility_sessions.discard(session_id)
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="comparator")
        draft = comparator.run(user_message, routing, session)

    elif intent == "catalog_query":
        _eligibility_sessions.discard(session_id)
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="catalog")
        draft = compliance_faq.run_catalog(user_message, session)

    elif intent == "eligibility_check" or in_eligibility:
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="eligibility")
        response, done = compliance_faq.run_eligibility(user_message, routing, session)
        if not done:
            _eligibility_sessions.add(session_id)
            clean = _guardrails(response)
            session.add(user_message, clean)
            log_event(
                "eligibility_progress",
                request_id=request_id,
                session_id=session_id,
                complete=False,
                response_chars=len(clean),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return clean
        _eligibility_sessions.discard(session_id)
        draft = response

    elif intent == "existing_cardholder":
        _eligibility_sessions.discard(session_id)
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="cardholder_service")
        draft = cardholder_svc.run(user_message, routing, session)

    elif intent == "i_need_a_credit_card":
        _eligibility_sessions.discard(session_id)
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_advisor")
        draft = product_advisor.run(user_message, routing, session)

    else:
        _eligibility_sessions.discard(session_id)
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="faq_compliance")
        draft = compliance_faq.run_faq(user_message, routing, session)

    final_response = synthesis_agent.run(draft, user_message)
    clean = _guardrails(final_response)
    session.add(user_message, clean)
    log_event(
        "pipeline_complete",
        request_id=request_id,
        session_id=session_id,
        intent=intent,
        response_chars=len(clean),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return clean

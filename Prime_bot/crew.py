from classifier.intent_classifier import classify
from memory.session_memory import SessionMemory
from tools.rag_tool import list_all_products
import re
import time
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
_discovery_sessions: dict[str, dict] = {}

SERVICE_ID_PATTERNS = {"_services_", "cardholder_services", "conv_services", "islami_services"}

MAX_DISCOVERY_RETRIES = 3


def _guardrails(response: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
    if not cleaned or len(cleaned) < 10:
        return (
            "I'm sorry, I couldn't find relevant information in my knowledge base for that query. "
            "Please contact Prime Bank directly at **16218** or visit any Prime Bank branch for assistance."
        )
    return cleaned


def _is_service_product(product: dict) -> bool:
    pid = (product.get("product_id") or "").lower()
    pname = (product.get("product_name") or "").lower()
    for pattern in SERVICE_ID_PATTERNS:
        if pattern in pid or pattern in pname:
            return True
    if "cardholder" in pname and "service" in pname:
        return True
    return False


def _detect_banking_preference(user_message: str) -> str | None:
    from classifier.intent_classifier import _parse_json, VALID_BANKING
    from llm.ollama_client import chat as llm_chat

    system = """The user was asked: "Would you prefer conventional or Islamic (Shariah-compliant) banking?"
Based on their reply, which did they choose?

- conventional: standard banking, conventional, regular, normal
- islami: islamic, shariah, halal, hasanah, interest-free
- both: cannot determine from their reply

Respond ONLY with JSON: {"banking_type": "<type>"}"""

    result = llm_chat(
        messages=[{"role": "user", "content": user_message}],
        system=system,
        temperature=0.0,
        max_tokens=300,
    )
    banking = _parse_json(result)
    banking_type = banking.get("banking_type", None)
    if banking_type and banking_type in VALID_BANKING and banking_type != "both":
        return banking_type
    return None


def _build_filtered_card_response(banking_type: str) -> str:
    all_products = list_all_products()
    cards = [
        p for p in all_products
        if not _is_service_product(p) and p["banking_type"] == banking_type
    ]

    if not cards:
        return (
            f"I couldn't find {banking_type} cards in my catalog. "
            "Please contact Prime Bank at **16218** for assistance."
        )

    label = (
        "Conventional" if banking_type == "conventional"
        else "Islamic (Shariah-compliant)"
    )

    tiers: dict[str, list] = {}
    for p in cards:
        tier = (p.get("tier") or "other").capitalize()
        tiers.setdefault(tier, []).append(p)

    lines = [f"Here are Prime Bank's **{label}** credit cards:\n"]
    for tier_name, tier_cards in tiers.items():
        lines.append(f"**{tier_name} Tier:**")
        for p in tier_cards:
            name = p["product_name"]
            network = f" ({p['card_network']})" if p.get("card_network") else ""
            lines.append(f"  - **{name}**{network}")
        lines.append("")

    lines.append(
        "What will be the primary use case for your card — **travel**, **dining**, "
        "**shopping**, **rewards**, or **premium lifestyle**?"
    )
    return "\n".join(lines)


def _build_all_cards_response() -> str | None:
    all_products = list_all_products()
    if not all_products:
        return None

    cards_only = [p for p in all_products if not _is_service_product(p)]
    if not cards_only:
        return None

    conventional = [p for p in cards_only if p["banking_type"] == "conventional"]
    islami = [p for p in cards_only if p["banking_type"] == "islami"]

    lines = []
    if conventional:
        lines.append("**Conventional Banking:**")
        for p in conventional:
            name = p["product_name"]
            parts = [f"  - {name}"]
            if p.get("card_network"):
                parts.append(f"({p['card_network']})")
            if p.get("tier"):
                parts.append(f"— {p['tier'].capitalize()}")
            lines.append(" ".join(parts))

    if islami:
        lines.append("\n**Islamic (Shariah-compliant) Banking:**")
        for p in islami:
            name = p["product_name"]
            parts = [f"  - {name}"]
            if p.get("card_network"):
                parts.append(f"({p['card_network']})")
            if p.get("tier"):
                parts.append(f"— {p['tier'].capitalize()}")
            lines.append(" ".join(parts))

    product_list = "\n".join(lines)

    return (
        f"Great! Prime Bank offers **{len(cards_only)} credit cards** across two banking types:\n\n"
        f"{product_list}\n\n"
        f"Would you prefer **conventional** or **Islamic (Shariah-compliant)** banking?"
    )


def build_crew(user_message: str, session: SessionMemory, request_id: str | None = None) -> str:
    started = time.perf_counter()
    session_id = session.session_id
    in_eligibility = session_id in _eligibility_sessions
    in_discovery = session_id in _discovery_sessions

    if in_discovery:
        state = _discovery_sessions.get(session_id, {"step": 0, "retries": 0})
        step = state.get("step", 0)

        classifier_output = classify(user_message)
        log_event(
            "classifier_result",
            request_id=request_id,
            session_id=session_id,
            intent=classifier_output.get("intent"),
            banking_type=classifier_output.get("banking_type"),
            intent_score=round(classifier_output.get("intent_score", 0.0), 4),
            banking_score=round(classifier_output.get("banking_score", 0.0), 4),
        )

        breakout_intents = {"comparison", "eligibility_check", "existing_cardholder", "how_to_apply", "product_details"}
        if classifier_output["intent"] in breakout_intents:
            _discovery_sessions.pop(session_id, None)
            return _handle_intent(user_message, classifier_output, session, request_id, started)

        if step == 0:
            banking_pref = _detect_banking_preference(user_message)

            if banking_pref:
                session.update_profile("banking_preference", banking_pref)
                state["banking_type"] = banking_pref
                state["step"] = 1
                state["retries"] = 0
                _discovery_sessions[session_id] = state

                response = _build_filtered_card_response(banking_pref)
                clean = _guardrails(response)
                session.add(user_message, clean)
                log_event(
                    "discovery_step",
                    request_id=request_id,
                    session_id=session_id,
                    step=1,
                    banking_type=banking_pref,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                )
                return clean
            else:
                state["retries"] = state.get("retries", 0) + 1
                if state["retries"] >= MAX_DISCOVERY_RETRIES:
                    _discovery_sessions.pop(session_id, None)
                else:
                    _discovery_sessions[session_id] = state
                    response = (
                        "Could you please specify — would you prefer "
                        "**conventional** or **Islamic (Shariah-compliant)** banking?"
                    )
                    session.add(user_message, response)
                    return response

        elif step == 1:
            banking_type = state.get("banking_type", "both")
            _discovery_sessions.pop(session_id, None)

            routing = {
                "intent": "i_need_a_credit_card",
                "banking_type": banking_type,
                "collection": f"{banking_type}_credit_i_need_a_credit_card",
                "search_query": user_message,
            }

            log_event(
                "specialist_start",
                request_id=request_id,
                session_id=session_id,
                specialist="product_advisor",
            )
            draft = product_advisor.run(user_message, routing, session)
            final_response = synthesis_agent.run(draft, user_message)
            clean = _guardrails(final_response)
            session.add(user_message, clean)
            log_event(
                "pipeline_complete",
                request_id=request_id,
                session_id=session_id,
                intent="discovery_recommendation",
                banking_type=banking_type,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return clean

    if in_eligibility:
        classifier_output = classify(user_message)
        log_event(
            "classifier_result",
            request_id=request_id,
            session_id=session_id,
            intent=classifier_output.get("intent"),
            banking_type=classifier_output.get("banking_type"),
            intent_score=round(classifier_output.get("intent_score", 0.0), 4),
            banking_score=round(classifier_output.get("banking_score", 0.0), 4),
        )

        text = user_message.strip().lower()
        if text in ("skip", "cancel", "stop", "exit", "nevermind", "never mind"):
            _eligibility_sessions.discard(session_id)
        else:
            log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="eligibility")
            response, done = compliance_faq.run_eligibility(user_message, {"banking_type": "both"}, session, is_new_check=False)
            if not done:
                clean = _guardrails(response)
                session.add(user_message, clean)
                return clean
            _eligibility_sessions.discard(session_id)
            draft = response
            final_response = synthesis_agent.run(draft, user_message)
            clean = _guardrails(final_response)
            session.add(user_message, clean)
            log_event(
                "pipeline_complete",
                request_id=request_id,
                session_id=session_id,
                intent="eligibility_check",
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return clean

    classifier_output = classify(user_message)
    log_event(
        "classifier_result",
        request_id=request_id,
        session_id=session_id,
        intent=classifier_output.get("intent"),
        banking_type=classifier_output.get("banking_type"),
        intent_score=round(classifier_output.get("intent_score", 0.0), 4),
        banking_score=round(classifier_output.get("banking_score", 0.0), 4),
    )

    intent = classifier_output["intent"]

    if intent == "i_need_a_credit_card" and len(session.history) == 0:
        discovery_response = _build_all_cards_response()
        if discovery_response:
            _discovery_sessions[session_id] = {"step": 0, "retries": 0}
            clean = _guardrails(discovery_response)
            session.add(user_message, clean)
            log_event(
                "discovery_response",
                request_id=request_id,
                session_id=session_id,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return clean

    return _handle_intent(user_message, classifier_output, session, request_id, started)


def _handle_intent(
    user_message: str,
    classifier_output: dict,
    session: SessionMemory,
    request_id: str | None,
    started: float,
) -> str:
    session_id = session.session_id
    intent = classifier_output["intent"]
    banking_type = classifier_output["banking_type"]

    routing = {
        "intent": intent,
        "banking_type": banking_type,
        "collection": f"{banking_type}_credit_i_need_a_credit_card" if banking_type != "both" else "all_products",
        "search_query": user_message,
    }

    log_event(
        "route_selected",
        request_id=request_id,
        session_id=session_id,
        intent=intent,
        banking_type=banking_type,
    )

    if intent == "comparison":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="comparator")
        draft = comparator.run(user_message, routing, session)

    elif intent == "catalog_query":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="catalog")
        draft = compliance_faq.run_catalog(user_message, session)

    elif intent == "eligibility_check":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="eligibility")
        session.update_profile("eligibility_target", user_message)
        response, done = compliance_faq.run_eligibility(user_message, routing, session, is_new_check=True)
        if not done:
            _eligibility_sessions.add(session_id)
            clean = _guardrails(response)
            session.add(user_message, clean)
            return clean
        draft = response

    elif intent == "existing_cardholder":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="cardholder_service")
        draft = cardholder_svc.run(user_message, routing, session)

    elif intent == "i_need_a_credit_card":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_advisor")
        draft = product_advisor.run(user_message, routing, session)

    elif intent == "how_to_apply":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="how_to_apply")
        draft = compliance_faq.run_apply(user_message, routing, session)

    elif intent == "product_details":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_details")
        draft = product_advisor.run_details(user_message, routing, session)

    else:
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
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return clean
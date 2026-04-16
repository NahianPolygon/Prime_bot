from classifier.intent_classifier import classify
from memory.session_memory import SessionMemory
from tools.rag_tool import list_all_products
import re
import json
import time
from typing import Generator
import agents.product_advisor as product_advisor
import agents.cardholder_svc as cardholder_svc
import agents.comparator as comparator
import agents.compliance_faq as compliance_faq
import agents.synthesis_agent as synthesis_agent
import yaml
from logging_utils import log_event

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_discovery_sessions: dict[str, dict] = {}


EXPLICIT_ISLAMI_KEYWORDS = {"halal", "islamic", "shariah", "sharia", "hasanah", "hasannah", "hasnah"}
EXPLICIT_CONVENTIONAL_KEYWORDS = {"conventional", "regular", "standard"}


def _explicit_banking_from_message(user_message: str) -> str | None:
    msg = user_message.lower()
    if any(kw in msg for kw in EXPLICIT_ISLAMI_KEYWORDS):
        return "islami"
    if any(kw in msg for kw in EXPLICIT_CONVENTIONAL_KEYWORDS):
        return "conventional"
    return None

SERVICE_ID_PATTERNS = {"_services_", "cardholder_services", "conv_services", "islami_services"}

MAX_DISCOVERY_RETRIES = 3

FILTER_EXTRACT_SYSTEM = """You extract credit card filters from a user's message.

Return ONLY a JSON object with these optional keys:
- banking_type: "conventional" or "islami" (if user mentions islamic, shariah, halal, hasanah, conventional, regular, standard)
- network: "visa" or "mastercard" or "jcb" (if user mentions a specific card network)
- tier: "gold" or "platinum" or "world" (if user mentions a specific card tier/level)

Rules:
- Only include keys where the user clearly expressed a preference
- "halal", "shariah", "islamic" means banking_type is "islami"
- "regular", "standard", "conventional" means banking_type is "conventional"
- "premium", "high-end", "top-tier" means tier is "world"
- "mid-range", "mid-tier" means tier is "platinum"
- "basic", "entry", "starter", "beginner" means tier is "gold"
- Return {} if no specific filter can be determined

Examples:
"I need a halal credit card" -> {"banking_type": "islami"}
"Show me all Visa cards" -> {"network": "visa"}
"What platinum cards do you have" -> {"tier": "platinum"}
"Show me Islamic gold cards" -> {"banking_type": "islami", "tier": "gold"}
"I want a premium Mastercard" -> {"network": "mastercard", "tier": "world"}
"Show me entry level cards" -> {"tier": "gold"}
"I need a credit card" -> {}
"What cards do you offer" -> {}

JSON only. No explanation."""


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


def _detect_card_filters(user_message: str) -> dict:
    from llm.ollama_client import chat as llm_chat

    result = llm_chat(
        messages=[{"role": "user", "content": user_message}],
        system=FILTER_EXTRACT_SYSTEM,
        temperature=0.0,
        max_tokens=200,
    )

    try:
        cleaned = re.sub(r'```(?:json)?', '', result).strip()
        match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            valid = {}
            if parsed.get("banking_type") in ("conventional", "islami"):
                valid["banking_type"] = parsed["banking_type"]
            if parsed.get("network") in ("visa", "mastercard", "jcb"):
                valid["network"] = parsed["network"]
            if parsed.get("tier") in ("gold", "platinum", "world"):
                valid["tier"] = parsed["tier"]
            return valid
    except Exception:
        pass

    return {}


def _build_dynamic_card_response(filters: dict) -> str | None:
    all_products = list_all_products()
    if not all_products:
        return None

    cards = [p for p in all_products if not _is_service_product(p)]

    filter_labels = []

    if "banking_type" in filters:
        cards = [p for p in cards if p["banking_type"] == filters["banking_type"]]
        label = "Conventional" if filters["banking_type"] == "conventional" else "Islamic (Shariah-compliant)"
        filter_labels.append(label)

    if "network" in filters:
        cards = [p for p in cards if (p.get("card_network") or "").lower() == filters["network"]]
        filter_labels.append(filters["network"].capitalize())

    if "tier" in filters:
        cards = [p for p in cards if (p.get("tier") or "").lower() == filters["tier"]]
        filter_labels.append(filters["tier"].capitalize())

    if not cards:
        filter_desc = " ".join(filter_labels) if filter_labels else ""
        return (
            f"I couldn't find any {filter_desc} cards in my catalog. "
            "Please contact Prime Bank at **16218** for assistance."
        )

    filter_desc = " ".join(filter_labels) if filter_labels else ""
    has_banking = "banking_type" in filters

    conventional = [p for p in cards if p["banking_type"] == "conventional"]
    islami = [p for p in cards if p["banking_type"] == "islami"]

    lines = [f"Here are Prime Bank's **{filter_desc}** credit cards ({len(cards)} found):\n"]

    if conventional:
        if not has_banking:
            lines.append("**Conventional Banking:**")
        for p in conventional:
            name = p["product_name"]
            parts = [f"  - **{name}**"]
            if p.get("card_network") and "network" not in filters:
                parts.append(f"({p['card_network']})")
            if p.get("tier") and "tier" not in filters:
                parts.append(f"— {p['tier'].capitalize()}")
            lines.append(" ".join(parts))

    if islami:
        if not has_banking:
            lines.append("\n**Islamic (Shariah-compliant) Banking:**")
        for p in islami:
            name = p["product_name"]
            parts = [f"  - **{name}**"]
            if p.get("card_network") and "network" not in filters:
                parts.append(f"({p['card_network']})")
            if p.get("tier") and "tier" not in filters:
                parts.append(f"— {p['tier'].capitalize()}")
            lines.append(" ".join(parts))

    lines.append("")

    if has_banking:
        if len(cards) <= 3:
            lines.append(
                "Would you like to see details about any of these cards, "
                "compare them, or check your eligibility?"
            )
        else:
            lines.append(
                "What will be the primary use case for your card — **travel**, **dining**, "
                "**shopping**, **rewards**, or **premium lifestyle**?"
            )
    elif len(conventional) > 0 and len(islami) > 0:
        lines.append(
            "Would you prefer **conventional** or **Islamic (Shariah-compliant)** banking?"
        )
    else:
        lines.append(
            "Would you like details about any of these cards, or shall I recommend one based on your needs?"
        )

    return "\n".join(lines)


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

    if len(cards) <= 3:
        lines.append(
            "Would you like to see details about any of these cards, "
            "compare them, or check your eligibility?"
        )
    else:
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


def _needs_filter_extraction(user_message: str, banking_type: str) -> bool:
    if banking_type in ("conventional", "islami"):
        return True
    msg_lower = user_message.lower()
    return any(
        term in msg_lower
        for term in (
            "visa", "mastercard", "jcb", "gold", "platinum", "world",
            "premium", "entry", "basic", "starter", "top-tier", "high-end",
            "mid-range", "mid-tier", "halal", "islamic", "shariah", "hasanah",
            "conventional", "regular", "standard",
        )
    )


_OFF_TOPIC_SYSTEM = """You are a topic classifier for a bank credit card chatbot.
Decide if the user's message is related to banking, credit cards, loans, payments, or financial services.

Reply ONLY with JSON: {"on_topic": true} or {"on_topic": false}

Examples:
"What is the annual fee?" -> {"on_topic": true}
"How do I apply for a card?" -> {"on_topic": true}
"Who won the World Cup?" -> {"on_topic": false}
"Tell me a joke" -> {"on_topic": false}
"What's the weather today?" -> {"on_topic": false}
"Hello" -> {"on_topic": true}
"""


def _is_off_topic(user_message: str) -> bool:
    from llm.ollama_client import chat as llm_chat
    try:
        result = llm_chat(
            messages=[{"role": "user", "content": user_message}],
            system=_OFF_TOPIC_SYSTEM,
            temperature=0.0,
            max_tokens=20,
            think=False,
        )
        cleaned = re.sub(r'```(?:json)?', '', result).strip()
        match = re.search(r'\{[^{}]*\}', cleaned)
        if match:
            parsed = json.loads(match.group())
            return not bool(parsed.get("on_topic", True))
    except Exception:
        pass
    return False


def _build_eligibility_form_signal(user_message: str, session: SessionMemory) -> str:
    history = session.get_history_str(max_chars=500)
    target = compliance_faq.extract_target_card(user_message, history)
    profile = session.user_profile if session.user_profile else None
    schema = compliance_faq.get_eligibility_form_schema(target, profile)
    intro = f"Please fill out the form below to check your eligibility{' for **' + target + '**' if target else ''}."
    session.add(user_message, intro)
    return json.dumps({"__form_signal__": True, "type": "show_eligibility_form", "schema": schema})


def _form_data_summary(form_data: dict) -> str:
    parts = []
    if form_data.get("target_card"):
        parts.append(f"Card: {form_data['target_card']}")
    parts.append(f"Age: {form_data.get('age', 'N/A')}")
    parts.append(f"Employment: {form_data.get('employment_type', 'N/A')}")
    parts.append(f"Income: {form_data.get('monthly_income', 'N/A')} BDT/month")
    years = form_data.get("employment_duration_years", 0)
    months = form_data.get("employment_duration_months", 0)
    parts.append(f"Experience: {years}y {months}m")
    parts.append(f"E-TIN: {'Yes' if form_data.get('has_etin') else 'No'}")
    return "Eligibility check — " + ", ".join(parts)


def _get_draft(
    user_message: str,
    classifier_output: dict,
    session: SessionMemory,
    request_id: str | None,
) -> tuple[str | None, str | None]:
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
        return draft, "no_synth"

    elif intent == "catalog_query":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="catalog")
        return compliance_faq.run_catalog(user_message, session), None

    elif intent == "eligibility_check":
        return "Please use the eligibility form to check your qualification.", "no_synth"

    elif intent == "existing_cardholder":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="cardholder_service")
        return cardholder_svc.run(user_message, routing, session), None

    elif intent == "i_need_a_credit_card":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_advisor")
        return product_advisor.run(user_message, routing, session), None

    elif intent == "how_to_apply":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="how_to_apply")
        return compliance_faq.run_apply(user_message, routing, session), None

    elif intent == "product_details":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_details")
        return product_advisor.run_details(user_message, routing, session), None

    else:
        if _is_off_topic(user_message):
            return (
                "I'm Prime Bank's credit card assistant and can only help with credit card products, "
                "eligibility, fees, rewards, and account services. "
                "Is there anything credit-card related I can help you with?"
            ), "no_synth"
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="faq_compliance")
        return compliance_faq.run_faq(user_message, routing, session), None


def _handle_intent(
    user_message: str,
    classifier_output: dict,
    session: SessionMemory,
    request_id: str | None,
    started: float,
) -> str:
    session_id = session.session_id
    intent = classifier_output["intent"]

    draft, mode = _get_draft(user_message, classifier_output, session, request_id)

    if mode == "no_synth":
        clean = _guardrails(draft)
        session.add(user_message, clean)
        log_event(
            "pipeline_complete",
            request_id=request_id,
            session_id=session_id,
            intent=intent,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return clean

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


def build_crew(user_message: str, session: SessionMemory, request_id: str | None = None) -> str:
    started = time.perf_counter()
    session_id = session.session_id
    in_discovery = session_id in _discovery_sessions
    history = session.get_history_str(max_chars=500)

    if in_discovery:
        state = _discovery_sessions.get(session_id, {"step": 0, "retries": 0})
        step = state.get("step", 0)

        classifier_output = classify(user_message, history)
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
            if classifier_output["intent"] == "eligibility_check":
                target = compliance_faq.extract_target_card(user_message, history)
                response = f"Please complete the eligibility form to check your qualification{' for ' + target if target else ''}."
                session.add(user_message, response)
                return response
            return _handle_intent(user_message, classifier_output, session, request_id, started)

        if step == 0:
            banking_pref = _detect_banking_preference(user_message)

            if banking_pref:
                session.update_profile("banking_preference", banking_pref)

                original_filters = state.get("filters", {})
                original_filters["banking_type"] = banking_pref
                merged_response = _build_dynamic_card_response(original_filters)

                if merged_response:
                    state["banking_type"] = banking_pref
                    state["step"] = 1
                    state["retries"] = 0
                    state["filters"] = original_filters
                    _discovery_sessions[session_id] = state

                    clean = _guardrails(merged_response)
                    session.add(user_message, clean)
                    log_event(
                        "discovery_step",
                        request_id=request_id,
                        session_id=session_id,
                        step=1,
                        banking_type=banking_pref,
                        filters=str(original_filters),
                        latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    )
                    return clean
                else:
                    response = _build_filtered_card_response(banking_pref)
                    state["banking_type"] = banking_pref
                    state["step"] = 1
                    state["retries"] = 0
                    _discovery_sessions[session_id] = state

                    clean = _guardrails(response)
                    session.add(user_message, clean)
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

    classifier_output = classify(user_message, history)
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

    if intent == "eligibility_check":
        target = compliance_faq.extract_target_card(user_message, history)
        response = f"Please complete the eligibility form to check your qualification{' for ' + target if target else ''}."
        session.add(user_message, response)
        return response

    if intent in ("i_need_a_credit_card", "catalog_query") and len(session.history) == 0:
        banking_type = classifier_output["banking_type"]

        if _needs_filter_extraction(user_message, banking_type):
            filters = _detect_card_filters(user_message)
        else:
            filters = {}

        if filters:
            response = _build_dynamic_card_response(filters)
            if response:
                bt = filters.get("banking_type", "both")
                if bt in ("conventional", "islami"):
                    session.update_profile("banking_preference", bt)
                    _discovery_sessions[session_id] = {
                        "step": 1,
                        "banking_type": bt,
                        "filters": filters,
                        "retries": 0,
                    }
                else:
                    _discovery_sessions[session_id] = {
                        "step": 0,
                        "filters": filters,
                        "retries": 0,
                    }

                clean = _guardrails(response)
                session.add(user_message, clean)
                log_event(
                    "discovery_response",
                    request_id=request_id,
                    session_id=session_id,
                    filters=str(filters),
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                )
                return clean

        discovery_response = _build_all_cards_response()
        if discovery_response:
            _discovery_sessions[session_id] = {"step": 0, "filters": {}, "retries": 0}
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


def handle_eligibility_form(
    form_data: dict,
    session: SessionMemory,
    request_id: str | None = None,
) -> str:
    started = time.perf_counter()
    session_id = session.session_id

    log_event(
        "eligibility_form_received",
        request_id=request_id,
        session_id=session_id,
        target_card=form_data.get("target_card", ""),
    )

    errors = compliance_faq.validate_eligibility_form(form_data)
    if errors:
        log_event(
            "eligibility_form_validation_failed",
            request_id=request_id,
            session_id=session_id,
            errors=errors,
        )
        return "**Please fix the following:**\n\n" + "\n".join(f"- {e}" for e in errors)

    user_summary = _form_data_summary(form_data)
    session.add(user_summary, "")

    draft = compliance_faq.run_eligibility(form_data, session)
    final_response = synthesis_agent.run(draft, user_summary)
    clean = _guardrails(final_response)

    clean_lower = clean.lower()
    if "✅" in clean or "eligible" in clean_lower and "not eligible" not in clean_lower:
        cta = (
            "\n\n**Ready to apply?** Visit any Prime Bank branch or call **16218** "
            "to start your application today."
        )
    elif "⚠️" in clean or "conditional" in clean_lower:
        cta = (
            "\n\nFor guidance on meeting the remaining requirements, "
            "call **16218** or visit a Prime Bank branch."
        )
    elif "❌" in clean or "not eligible" in clean_lower:
        cta = (
            "\n\nWould you like to explore other cards that may suit your profile? "
            "Call **16218** or visit a branch for personalised advice."
        )
    else:
        cta = "\n\nFor further assistance, contact Prime Bank at **16218** or visit any branch."
    clean = clean + cta

    session.history[-1]["content"] = clean
    session.history[-1]["content_short"] = session._truncate_for_history(clean)

    log_event(
        "eligibility_form_complete",
        request_id=request_id,
        session_id=session_id,
        target_card=form_data.get("target_card", ""),
        response_chars=len(clean),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )

    return clean


def _discovery_step1_stream(
    user_message: str,
    session: SessionMemory,
    request_id: str | None,
    started: float,
) -> Generator[str, None, None]:
    """Stream a product recommendation for the discovery step-1 path."""
    session_id = session.session_id
    state = _discovery_sessions.get(session_id, {})
    banking_type = state.get("banking_type", "both")
    history = session.get_history_str(max_chars=500)

    classifier_output = classify(user_message, history)
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
        if classifier_output["intent"] == "eligibility_check":
            yield _build_eligibility_form_signal(user_message, session)
            return
        draft, mode = _get_draft(user_message, classifier_output, session, request_id)
        if mode == "no_synth":
            clean = _guardrails(draft)
            session.add(user_message, clean)
            yield clean
            return
        collected = []
        for token in synthesis_agent.run_stream(draft, user_message):
            collected.append(token)
            yield token
        full = "".join(collected)
        clean = _guardrails(full)
        session.add(user_message, clean)
        return

    _discovery_sessions.pop(session_id, None)

    routing = {
        "intent": "i_need_a_credit_card",
        "banking_type": banking_type,
        "collection": f"{banking_type}_credit_i_need_a_credit_card",
        "search_query": user_message,
    }
    log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_advisor")
    draft = product_advisor.run(user_message, routing, session)

    collected = []
    for token in synthesis_agent.run_stream(draft, user_message):
        collected.append(token)
        yield token

    full_response = "".join(collected)
    clean = _guardrails(full_response)
    session.add(user_message, clean)
    log_event(
        "pipeline_complete_stream",
        request_id=request_id,
        session_id=session_id,
        intent="discovery_recommendation",
        banking_type=banking_type,
        response_chars=len(clean),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


def build_crew_stream(
    user_message: str,
    session: SessionMemory,
    request_id: str | None = None,
) -> Generator[str, None, None]:
    started = time.perf_counter()
    session_id = session.session_id
    in_discovery = session_id in _discovery_sessions
    history = session.get_history_str(max_chars=500)

    if in_discovery:
        state = _discovery_sessions.get(session_id, {"step": 0, "retries": 0})
        if state.get("step") == 1:
            for token in _discovery_step1_stream(user_message, session, request_id, started):
                yield token
            return

        result = _handle_discovery_stream(user_message, session, request_id, started)
        if result is not None:
            yield result
            return

    classifier_output = classify(user_message, history)
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

    if intent == "eligibility_check":
        yield _build_eligibility_form_signal(user_message, session)
        return

    if intent in ("i_need_a_credit_card", "catalog_query") and len(session.history) == 0:
        result = _handle_first_message_discovery(user_message, classifier_output, session, request_id, started)
        if result is not None:
            yield result
            return

    draft, mode = _get_draft(user_message, classifier_output, session, request_id)

    if mode == "no_synth":
        clean = _guardrails(draft)
        session.add(user_message, clean)
        log_event(
            "pipeline_complete",
            request_id=request_id,
            session_id=session_id,
            intent=intent,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        yield clean
        return

    collected = []
    for token in synthesis_agent.run_stream(draft, user_message):
        collected.append(token)
        yield token

    full_response = "".join(collected)
    clean = _guardrails(full_response)
    session.add(user_message, clean)
    log_event(
        "pipeline_complete_stream",
        request_id=request_id,
        session_id=session_id,
        intent=intent,
        response_chars=len(clean),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


def _handle_discovery_stream(
    user_message: str,
    session: SessionMemory,
    request_id: str | None,
    started: float,
) -> str | None:
    session_id = session.session_id
    state = _discovery_sessions.get(session_id, {"step": 0, "retries": 0})
    step = state.get("step", 0)
    history = session.get_history_str(max_chars=500)

    classifier_output = classify(user_message, history)
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
        if classifier_output["intent"] == "eligibility_check":
            return _build_eligibility_form_signal(user_message, session)
        return None

    if step == 0:
        banking_pref = _detect_banking_preference(user_message)

        if banking_pref:
            session.update_profile("banking_preference", banking_pref)

            original_filters = state.get("filters", {})
            original_filters["banking_type"] = banking_pref
            merged_response = _build_dynamic_card_response(original_filters)

            if merged_response:
                state["banking_type"] = banking_pref
                state["step"] = 1
                state["retries"] = 0
                state["filters"] = original_filters
                _discovery_sessions[session_id] = state

                clean = _guardrails(merged_response)
                session.add(user_message, clean)
                return clean
            else:
                response = _build_filtered_card_response(banking_pref)
                state["banking_type"] = banking_pref
                state["step"] = 1
                state["retries"] = 0
                _discovery_sessions[session_id] = state

                clean = _guardrails(response)
                session.add(user_message, clean)
                return clean
        else:
            state["retries"] = state.get("retries", 0) + 1
            if state["retries"] >= MAX_DISCOVERY_RETRIES:
                _discovery_sessions.pop(session_id, None)
                return None
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

        draft = product_advisor.run(user_message, routing, session)
        final_response = synthesis_agent.run(draft, user_message)
        clean = _guardrails(final_response)
        session.add(user_message, clean)
        return clean

    return None


def _handle_first_message_discovery(
    user_message: str,
    classifier_output: dict,
    session: SessionMemory,
    request_id: str | None,
    started: float,
) -> str | None:
    session_id = session.session_id
    banking_type = classifier_output["banking_type"]

    if _needs_filter_extraction(user_message, banking_type):
        filters = _detect_card_filters(user_message)
    else:
        filters = {}

    if not filters:
        explicit_bt = _explicit_banking_from_message(user_message)
        if explicit_bt:
            filters = {"banking_type": explicit_bt}

    if filters:
        response = _build_dynamic_card_response(filters)
        if response:
            bt = filters.get("banking_type", "both")
            if bt in ("conventional", "islami"):
                session.update_profile("banking_preference", bt)
                _discovery_sessions[session_id] = {
                    "step": 1,
                    "banking_type": bt,
                    "filters": filters,
                    "retries": 0,
                }
            else:
                _discovery_sessions[session_id] = {
                    "step": 0,
                    "filters": filters,
                    "retries": 0,
                }

            clean = _guardrails(response)
            session.add(user_message, clean)
            log_event(
                "discovery_response",
                request_id=request_id,
                session_id=session_id,
                filters=str(filters),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return clean

    discovery_response = _build_all_cards_response()
    if discovery_response:
        _discovery_sessions[session_id] = {"step": 0, "filters": {}, "retries": 0}
        clean = _guardrails(discovery_response)
        session.add(user_message, clean)
        log_event(
            "discovery_response",
            request_id=request_id,
            session_id=session_id,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return clean

    return None
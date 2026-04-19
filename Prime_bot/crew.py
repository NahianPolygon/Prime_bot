from classifier.intent_classifier import classify, classify_recommendation_followup, _parse_json
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
_preference_completed_sessions: set[str] = set()

SERVICE_ID_PATTERNS = {"_services_", "cardholder_services", "conv_services", "islami_services"}

MAX_DISCOVERY_RETRIES = 3
STREAM_CHUNK_CHARS = 48

_GREETING_RE = re.compile(r"^(hi|hello|hey|assalamu alaikum|salam|good morning|good afternoon|good evening)\b", re.IGNORECASE)
_OFF_TOPIC_HINT_RE = re.compile(
    r"\b(weather|world cup|football|cricket score|joke|movie|recipe|capital of|who won|news today)\b",
    re.IGNORECASE,
)


def _post_recommendation_fallback_intent(user_message: str) -> str | None:
    text = user_message.lower().strip()
    if not text:
        return None
    if any(term in text for term in ("eligib", "qualif", "approved", "can i get")):
        return "eligibility_check"
    if "compare" in text:
        return "comparison"
    if "apply" in text or "documents" in text:
        return "how_to_apply"
    if any(term in text for term in ("details", "tell me more", "more about", "benefits", "fee", "limit")):
        return "product_details"
    return None


def _stream_text(text: str, chunk_chars: int = STREAM_CHUNK_CHARS) -> Generator[str, None, None]:
    if not text:
        return
    for start in range(0, len(text), chunk_chars):
        yield text[start:start + chunk_chars]


def _special_case_response(user_message: str) -> str | None:
    text = user_message.strip()
    if not text:
        return None
    if _GREETING_RE.match(text):
        return (
            "Hello! I can help you with Prime Bank credit cards, eligibility, card comparison, "
            "application guidance, and existing cardholder services."
        )
    if _OFF_TOPIC_HINT_RE.search(text):
        return (
            "I'm Prime Bank's credit card assistant and can help with credit cards, eligibility, "
            "fees, rewards, applications, and cardholder services."
        )
    return None

DISCOVERY_SIGNAL_SYSTEM = """You analyze a Prime Bank credit card browsing message and extract browsing preferences.

Return ONLY JSON with this schema:
{"banking_type":"conventional"|"islami"|"both"|"","network":"visa"|"mastercard"|"jcb"|"","tier":"gold"|"platinum"|"world"|"","show_catalog":true|false}

Guidance:
- Use banking_type when the user clearly prefers conventional or Islamic banking
- Use network when the user clearly prefers Visa, Mastercard, or JCB
- Use tier when the user clearly prefers Gold, Platinum, or World tier
- Set show_catalog=true when the user is browsing, asking what cards are available, or answering a prior browsing follow-up
- Set fields to empty strings when not clearly expressed
- Infer semantically from the user's wording and the prior state
- Do not include any text outside the JSON"""


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


def _extract_discovery_signal(user_message: str, state: dict | None = None) -> dict:
    from classifier.intent_classifier import _parse_json
    from llm.ollama_client import chat as llm_chat

    state_json = json.dumps(state or {}, ensure_ascii=True)
    result = llm_chat(
        messages=[{"role": "user", "content": f"Discovery state: {state_json}\n\nUser message: {user_message}"}],
        system=DISCOVERY_SIGNAL_SYSTEM,
        temperature=0.0,
        max_tokens=180,
    )

    parsed = _parse_json(result)
    valid = {
        "banking_type": parsed.get("banking_type", ""),
        "network": parsed.get("network", ""),
        "tier": parsed.get("tier", ""),
        "show_catalog": bool(parsed.get("show_catalog", False)),
    }
    if valid["banking_type"] not in ("conventional", "islami", "both", ""):
        valid["banking_type"] = ""
    if valid["network"] not in ("visa", "mastercard", "jcb", ""):
        valid["network"] = ""
    if valid["tier"] not in ("gold", "platinum", "world", ""):
        valid["tier"] = ""
    return valid


def _filters_from_signal(signal: dict, classifier_output: dict | None = None) -> dict:
    filters = {}
    banking_type = signal.get("banking_type") or ""
    if not banking_type and classifier_output:
        classified = classifier_output.get("banking_type", "both")
        if classified in ("conventional", "islami"):
            banking_type = classified
    if banking_type in ("conventional", "islami"):
        filters["banking_type"] = banking_type
    if signal.get("network") in ("visa", "mastercard", "jcb"):
        filters["network"] = signal["network"]
    if signal.get("tier") in ("gold", "platinum", "world"):
        filters["tier"] = signal["tier"]
    return filters


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


_PROFILE_EXTRACT_SYSTEM = """Extract financial profile signals from this conversation history.
Return ONLY JSON: {"monthly_income":null,"employment_type":null,"age":null}
Fill in number values only when the user explicitly stated them.
monthly_income: monthly income in BDT as a number, or null
employment_type: exactly "salaried", "self_employed", or "business_owner", or null
age: age in years as a number, or null
Do not infer, estimate, or assume — only extract values the user directly stated."""


def _extract_profile_from_history(session: SessionMemory):
    history = session.get_history_str(max_chars=800)
    if not history:
        return
    from llm.ollama_client import chat as llm_chat
    try:
        result = llm_chat(
            messages=[{"role": "user", "content": history}],
            system=_PROFILE_EXTRACT_SYSTEM,
            temperature=0.0,
            max_tokens=100,
            think=False,
        )
        parsed = _parse_json(result)
        if parsed.get("monthly_income") and not session.user_profile.get("monthly_income"):
            session.update_profile("monthly_income", int(parsed["monthly_income"]))
        if parsed.get("employment_type") and not session.user_profile.get("employment_type"):
            session.update_profile("employment_type", parsed["employment_type"])
        if parsed.get("age") and not session.user_profile.get("age"):
            session.update_profile("age", int(parsed["age"]))
    except Exception:
        pass


def _build_eligibility_form_signal(user_message: str, session: SessionMemory) -> str:
    _extract_profile_from_history(session)
    history = session.get_history_str(max_chars=500)
    target = compliance_faq.extract_target_card(user_message, history)
    recommended = session.user_profile.get("recommended_cards", [])
    if not isinstance(recommended, list):
        recommended = []
    if not target:
        if len(recommended) == 1:
            target = recommended[0]
    profile = session.user_profile if session.user_profile else None
    schema = compliance_faq.get_eligibility_form_schema(
        target,
        profile,
        recommended_cards=recommended if len(recommended) > 1 else None,
    )
    if target:
        intro = f"Please fill out the form below to check your eligibility for **{target}**."
    elif recommended:
        intro = "Please fill out the form below to check your eligibility for your recommended cards."
    else:
        intro = "Please fill out the form below to check your eligibility."
    session.add(user_message, intro)
    return json.dumps({"__form_signal__": True, "type": "show_eligibility_form", "schema": schema})


def _build_preference_form_signal(user_message: str, session: SessionMemory) -> str:
    schema = compliance_faq.get_preference_form_schema()
    intro = "To find the best card for you, please fill out the quick preference form below."
    session.add(user_message, intro)
    return json.dumps({"__preference_form_signal__": True, "type": "show_preference_form", "schema": schema})


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
        return compliance_faq.run_catalog(user_message, session), "no_synth"

    elif intent == "eligibility_check":
        return "Please use the eligibility form to check your qualification.", "no_synth"

    elif intent == "existing_cardholder":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="cardholder_service")
        return cardholder_svc.run(user_message, routing, session), "no_synth"

    elif intent == "i_need_a_credit_card":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_advisor")
        return product_advisor.run(user_message, routing, session), "no_synth"

    elif intent == "how_to_apply":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="how_to_apply")
        return compliance_faq.run_apply(user_message, routing, session), "no_synth"

    elif intent == "product_details":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_details")
        return product_advisor.run_details(user_message, routing, session), "no_synth"

    else:
        if _is_off_topic(user_message):
            return (
                "I'm Prime Bank's credit card assistant and can only help with credit card products, "
                "eligibility, fees, rewards, and account services. "
                "Is there anything credit-card related I can help you with?"
            ), "no_synth"
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="faq_compliance")
        return compliance_faq.run_faq(user_message, routing, session), "no_synth"


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
    pieces: list[str] = []
    for token in build_crew_stream(user_message, session, request_id=request_id):
        if token.startswith('{"__'):
            continue
        pieces.append(token)
    return "".join(pieces).strip()


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
    clean = _guardrails(draft)

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


def handle_preference_form(
    form_data: dict,
    session: SessionMemory,
    request_id: str | None = None,
) -> str:
    started = time.perf_counter()
    session_id = session.session_id

    log_event(
        "preference_form_received",
        request_id=request_id,
        session_id=session_id,
        banking_type=form_data.get("banking_type", ""),
        use_case=form_data.get("use_case", ""),
    )

    user_summary = (
        f"Card preference — banking: {form_data.get('banking_type', 'any')}, "
        f"use case: {form_data.get('use_case', 'general')}, "
        f"income: {form_data.get('income_band', 'unknown')}, "
        f"travel: {form_data.get('travel_frequency', 'unknown')}, "
        f"tier: {form_data.get('tier_preference', 'unknown')}"
    )
    session.add(user_summary, "")

    draft = compliance_faq.run_card_recommendation(form_data, session)
    clean = _guardrails(draft)
    session.update_profile("recommended_cards", compliance_faq.extract_recommended_card_names(clean))

    clean += (
        "\n\n**Want to check if you qualify?** Just ask me to check your eligibility, "
        "or visit any Prime Bank branch to apply."
    )

    session.history[-1]["content"] = clean
    session.history[-1]["content_short"] = session._truncate_for_history(clean)

    _preference_completed_sessions.add(session_id)
    log_event(
        "preference_form_complete",
        request_id=request_id,
        session_id=session_id,
        response_chars=len(clean),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return clean


def clear_preference_session(session_id: str) -> None:
    _preference_completed_sessions.discard(session_id)
    _discovery_sessions.pop(session_id, None)


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
    if (
        classifier_output.get("intent") == "i_need_a_credit_card"
        and session_id in _preference_completed_sessions
        and session.user_profile.get("recommended_cards")
        and len(user_message.strip()) <= 60
    ):
        followup_label = classify_recommendation_followup(
            user_message,
            session.get_last_assistant_response(),
        )
        if followup_label == "eligibility":
            classifier_output["intent"] = "eligibility_check"
            classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.85)
        elif followup_label == "compare":
            classifier_output["intent"] = "comparison"
            classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.85)
        elif followup_label == "apply":
            classifier_output["intent"] = "how_to_apply"
            classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.85)
        elif followup_label == "details":
            classifier_output["intent"] = "product_details"
            classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.85)
        elif followup_label == "other":
            fallback_intent = _post_recommendation_fallback_intent(user_message)
            if fallback_intent:
                classifier_output["intent"] = fallback_intent
                classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.84)
    log_event(
        "classifier_result",
        request_id=request_id,
        session_id=session_id,
        intent=classifier_output.get("intent"),
        banking_type=classifier_output.get("banking_type"),
        intent_score=round(classifier_output.get("intent_score", 0.0), 4),
        banking_score=round(classifier_output.get("banking_score", 0.0), 4),
    )

    breakout_intents = {"comparison", "eligibility_check", "existing_cardholder", "how_to_apply", "product_details", "i_need_a_credit_card"}
    if classifier_output["intent"] in breakout_intents:
        _discovery_sessions.pop(session_id, None)
        if classifier_output["intent"] == "eligibility_check":
            yield _build_eligibility_form_signal(user_message, session)
            return
        if classifier_output["intent"] == "i_need_a_credit_card":
            yield _build_preference_form_signal(user_message, session)
            return
        draft, mode = _get_draft(user_message, classifier_output, session, request_id)
        if mode == "no_synth":
            clean = _guardrails(draft)
            session.add(user_message, clean)
            for token in _stream_text(clean):
                yield token
            return
        collected = []
        for token in synthesis_agent.run_stream(draft, user_message):
            collected.append(token)
            yield token
        full = "".join(collected)
        clean = _guardrails(full)
        session.add(user_message, clean)
        if not full.strip():
            for token in _stream_text(clean):
                yield token
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
    if not full_response.strip():
        for token in _stream_text(clean):
            yield token
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
    special_case = _special_case_response(user_message)

    if special_case:
        clean = _guardrails(special_case)
        session.add(user_message, clean)
        for token in _stream_text(clean):
            yield token
        yield json.dumps({"__done_signal__": True, "intent": "general", "calculator": ""})
        return

    if in_discovery:
        state = _discovery_sessions.get(session_id, {"step": 0, "retries": 0})
        if state.get("step") == 1:
            for token in _discovery_step1_stream(user_message, session, request_id, started):
                yield token
            yield json.dumps({"__done_signal__": True, "intent": "i_need_a_credit_card", "calculator": ""})
            return

        had_discovery = False
        for token in _handle_discovery_stream_gen(user_message, session, request_id, started):
            had_discovery = True
            yield token
        if had_discovery:
            yield json.dumps({"__done_signal__": True, "intent": "discovery", "calculator": ""})
            return

    classifier_output = classify(user_message, history)
    if (
        classifier_output.get("intent") == "i_need_a_credit_card"
        and session_id in _preference_completed_sessions
        and session.user_profile.get("recommended_cards")
        and len(user_message.strip()) <= 60
    ):
        followup_label = classify_recommendation_followup(
            user_message,
            session.get_last_assistant_response(),
        )
        if followup_label == "eligibility":
            classifier_output["intent"] = "eligibility_check"
            classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.85)
        elif followup_label == "compare":
            classifier_output["intent"] = "comparison"
            classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.85)
        elif followup_label == "apply":
            classifier_output["intent"] = "how_to_apply"
            classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.85)
        elif followup_label == "details":
            classifier_output["intent"] = "product_details"
            classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.85)
        elif followup_label == "other":
            fallback_intent = _post_recommendation_fallback_intent(user_message)
            if fallback_intent:
                classifier_output["intent"] = fallback_intent
                classifier_output["intent_score"] = max(classifier_output.get("intent_score", 0.0), 0.84)
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
    calculator_type = classifier_output.get("calculator_type", "")
    intent_score = classifier_output.get("intent_score", 0.9)

    if intent == "eligibility_check":
        yield _build_eligibility_form_signal(user_message, session)
        yield json.dumps({"__done_signal__": True, "intent": "", "calculator": ""})
        return

    if intent == "i_need_a_credit_card" and session_id not in _preference_completed_sessions:
        yield _build_preference_form_signal(user_message, session)
        yield json.dumps({"__done_signal__": True, "intent": "", "calculator": ""})
        return

    if intent == "catalog_query" and len(session.history) == 0:
        had_first = False
        for token in _handle_first_message_discovery_stream(user_message, classifier_output, session, request_id, started):
            had_first = True
            yield token
        if had_first:
            yield json.dumps({"__done_signal__": True, "intent": intent, "calculator": calculator_type})
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
        for token in _stream_text(clean):
            yield token
        yield json.dumps({"__done_signal__": True, "intent": intent, "calculator": calculator_type})
        return

    collected = []
    for token in synthesis_agent.run_stream(draft, user_message):
        collected.append(token)
        yield token

    full_response = "".join(collected)
    clean = _guardrails(full_response)
    session.add(user_message, clean)
    if not full_response.strip():
        for token in _stream_text(clean):
            yield token
    yield json.dumps({"__done_signal__": True, "intent": intent, "calculator": calculator_type})
    log_event(
        "pipeline_complete_stream",
        request_id=request_id,
        session_id=session_id,
        intent=intent,
        response_chars=len(clean),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


def _handle_discovery_stream_gen(
    user_message: str,
    session: SessionMemory,
    request_id: str | None,
    started: float,
) -> Generator[str, None, None]:
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

    breakout_intents = {"comparison", "eligibility_check", "existing_cardholder", "how_to_apply", "product_details", "i_need_a_credit_card"}
    if classifier_output["intent"] in breakout_intents:
        _discovery_sessions.pop(session_id, None)
        if classifier_output["intent"] == "eligibility_check":
            yield _build_eligibility_form_signal(user_message, session)
        elif classifier_output["intent"] == "i_need_a_credit_card":
            yield _build_preference_form_signal(user_message, session)
        return

    if step == 0:
        signal = _extract_discovery_signal(user_message, state)
        original_filters = dict(state.get("filters", {}))
        original_filters.update(_filters_from_signal(signal, classifier_output))
        banking_pref = original_filters.get("banking_type")

        if banking_pref:
            session.update_profile("banking_preference", banking_pref)
            merged_response = _build_dynamic_card_response(original_filters)

            if merged_response:
                state["banking_type"] = banking_pref
                state["step"] = 1
                state["retries"] = 0
                state["filters"] = original_filters
                _discovery_sessions[session_id] = state

                clean = _guardrails(merged_response)
                session.add(user_message, clean)
                for token in _stream_text(clean):
                    yield token
                log_event(
                    "discovery_step",
                    request_id=request_id,
                    session_id=session_id,
                    step=1,
                    banking_type=banking_pref,
                    filters=str(original_filters),
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                )
            else:
                response = _build_filtered_card_response(banking_pref)
                state["banking_type"] = banking_pref
                state["step"] = 1
                state["retries"] = 0
                _discovery_sessions[session_id] = state

                clean = _guardrails(response)
                session.add(user_message, clean)
                for token in _stream_text(clean):
                    yield token
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
                for token in _stream_text(response):
                    yield token

    elif step == 1:
        banking_type = state.get("banking_type", "both")
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
        full = "".join(collected)
        clean = _guardrails(full if full.strip() else draft)
        session.add(user_message, clean)
        if not full.strip():
            for token in _stream_text(clean):
                yield token
        log_event(
            "pipeline_complete_stream",
            request_id=request_id,
            session_id=session_id,
            intent="discovery_recommendation",
            banking_type=banking_type,
            response_chars=len(clean),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )


def _handle_first_message_discovery_stream(
    user_message: str,
    classifier_output: dict,
    session: SessionMemory,
    request_id: str | None,
    started: float,
) -> Generator[str, None, None]:
    session_id = session.session_id
    signal = _extract_discovery_signal(user_message, {"step": "initial"})
    filters = _filters_from_signal(signal, classifier_output)

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
            for token in _stream_text(clean):
                yield token
            log_event(
                "discovery_response",
                request_id=request_id,
                session_id=session_id,
                filters=str(filters),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return

    discovery_response = _build_all_cards_response()
    if discovery_response:
        _discovery_sessions[session_id] = {"step": 0, "filters": {}, "retries": 0}

        clean = _guardrails(discovery_response)
        session.add(user_message, clean)
        for token in _stream_text(clean):
            yield token
        log_event(
            "discovery_response",
            request_id=request_id,
            session_id=session_id,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

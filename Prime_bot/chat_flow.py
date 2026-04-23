import json
import re
import time
from typing import Generator

import agents.cardholder_svc as cardholder_svc
import agents.comparator as comparator
import agents.compliance_faq as compliance_faq
import agents.product_advisor as product_advisor
from classifier.intent_classifier import _parse_json, classify
from logging_utils import log_event
from memory.session_memory import SessionMemory
from streaming_utils import iter_text_stream

_PROFILE_EXTRACT_SYSTEM = """Extract financial profile signals from this conversation history.
Return ONLY JSON: {"monthly_income":null,"employment_type":null,"age":null}
Fill in number values only when the user explicitly stated them.
monthly_income: monthly income in BDT as a number, or null
employment_type: exactly "salaried", "self_employed", or "business_owner", or null
age: age in years as a number, or null
Do not infer, estimate, or assume."""

_K_INCOME_RE = re.compile(r"(\d+(?:\.\d+)?)\s*k\b", re.IGNORECASE)
_DIGIT_INCOME_RE = re.compile(r"\b(\d{4,7})\b")


def _stream_text(text: str, chunk_chars: int = 24) -> Generator[str, None, None]:
    for chunk in iter_text_stream(text, chunk_chars=chunk_chars):
        yield chunk


def _guardrails(response: str) -> str:
    cleaned = (response or "").strip()
    if cleaned.startswith("[ERROR]"):
        return "I could not complete that request just now. Please try again."
    if cleaned.startswith("[NO RESULTS]"):
        return "I could not find that in my knowledge base. Please contact Prime Bank at **16218** for assistance."
    if not cleaned:
        return "I could not find that in my knowledge base. Please contact Prime Bank at **16218** for assistance."
    return cleaned


def _extract_profile_from_history(session: SessionMemory) -> None:
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
        return


def _build_eligibility_form_signal(user_message: str, session: SessionMemory) -> str:
    _extract_profile_from_history(session)
    target = compliance_faq.extract_target_card(user_message, "")
    recommended = session.user_profile.get("recommended_cards", [])
    if not isinstance(recommended, list):
        recommended = []
    if not target and len(recommended) == 1:
        target = recommended[0]
    profile = session.user_profile if session.user_profile else None
    schema = compliance_faq.get_eligibility_form_schema(
        target,
        profile,
        recommended_cards=recommended if len(recommended) > 1 else None,
    )
    intro = "Please fill out the form below to check your eligibility."
    if target:
        intro = f"Please fill out the form below to check your eligibility for **{target}**."
    elif recommended:
        intro = "Please fill out the form below to check your eligibility for your recommended cards."
    session.add(user_message, intro)
    return json.dumps({"__form_signal__": True, "type": "show_eligibility_form", "schema": schema})


def _infer_income_band_from_text(text: str) -> str:
    lowered = (text or "").lower()
    match_k = _K_INCOME_RE.search(lowered)
    amount = None
    if match_k:
        amount = float(match_k.group(1)) * 1000
    else:
        match_digits = _DIGIT_INCOME_RE.search(lowered.replace(",", ""))
        if match_digits:
            try:
                amount = float(match_digits.group(1))
            except ValueError:
                amount = None

    if amount is None:
        return ""
    if amount < 50_000:
        return "under_50k"
    if amount < 100_000:
        return "50k_100k"
    if amount < 200_000:
        return "100k_200k"
    return "200k_plus"


def _build_preference_prefill(user_message: str, session: SessionMemory, classifier_output: dict) -> dict:
    prefill: dict = {}
    lowered = (user_message or "").lower()

    banking_type = classifier_output.get("banking_type")
    if banking_type in ("conventional", "islami"):
        prefill["banking_type"] = banking_type
    elif session.user_profile.get("active_banking_type") in ("conventional", "islami"):
        prefill["banking_type"] = session.user_profile.get("active_banking_type")

    income_band = _infer_income_band_from_text(user_message)
    if not income_band:
        monthly_income = session.user_profile.get("monthly_income")
        if monthly_income:
            income_band = _infer_income_band_from_text(str(monthly_income))
    if income_band:
        prefill["income_band"] = income_band

    if any(term in lowered for term in ("travel", "lounge", "airport", "trip", "abroad")):
        prefill["use_case"] = "travel"
    elif any(term in lowered for term in ("dining", "restaurant", "lifestyle")):
        prefill["use_case"] = "dining"
    elif any(term in lowered for term in ("reward", "cashback", "points")):
        prefill["use_case"] = "rewards_earning"
    elif any(term in lowered for term in ("business", "office", "corporate")):
        prefill["use_case"] = "business_spending"
    elif any(term in lowered for term in ("shop", "shopping", "daily use", "everyday")):
        prefill["use_case"] = "shopping"
    elif any(term in lowered for term in ("first card", "first premium", "new card")):
        prefill["use_case"] = "entry_level_premium"

    if any(term in lowered for term in ("premium", "platinum", "world", "signature")):
        prefill["tier_preference"] = "premium"
    elif any(term in lowered for term in ("gold", "accessible", "entry")):
        prefill["tier_preference"] = "gold"

    if any(term in lowered for term in ("frequent travel", "travel often", "frequently")):
        prefill["travel_frequency"] = "frequent"
    elif any(term in lowered for term in ("sometimes", "occasional", "occasionally")):
        prefill["travel_frequency"] = "occasional"
    elif any(term in lowered for term in ("rarely", "rare travel", "hardly travel")):
        prefill["travel_frequency"] = "rare"

    return prefill


def _build_preference_form_signal(user_message: str, session: SessionMemory, classifier_output: dict) -> str:
    prefill = _build_preference_prefill(user_message, session, classifier_output)
    schema = compliance_faq.get_preference_form_schema(prefill=prefill or None)
    intro = "To recommend the best Prime Bank credit card for you, please fill out the quick preference form below."
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


def _build_routing(user_message: str, classifier_output: dict) -> dict:
    banking_type = classifier_output["banking_type"]
    collection = "all_products" if banking_type == "both" else f"{banking_type}_credit_i_need_a_credit_card"
    return {
        "intent": classifier_output["intent"],
        "banking_type": banking_type,
        "collection": collection,
        "search_query": classifier_output.get("search_query") or user_message,
        "active_cards": classifier_output.get("active_cards") or [],
    }


def _get_context_cards(session: SessionMemory) -> list[str]:
    cards = session.user_profile.get("active_cards") or session.user_profile.get("recommended_cards") or []
    if isinstance(cards, list) and cards:
        return cards

    verdicts = session.user_profile.get("last_eligibility_verdicts") or []
    if isinstance(verdicts, list):
        verdict_cards = [item.get("card_name", "") for item in verdicts if isinstance(item, dict) and item.get("card_name")]
        if verdict_cards:
            _remember_active_cards(session, verdict_cards, session.user_profile.get("active_banking_type", ""))
            return verdict_cards

    last_response = session.get_last_assistant_response()
    recovered_cards = compliance_faq.extract_recommended_card_names(last_response)
    if recovered_cards:
        _remember_active_cards(session, recovered_cards, session.user_profile.get("active_banking_type", ""))
        return recovered_cards

    return []


def _remember_active_cards(session: SessionMemory, cards: list[str], banking_type: str = "") -> None:
    if cards:
        session.update_profile("active_cards", cards)
    if banking_type in ("conventional", "islami"):
        session.update_profile("active_banking_type", banking_type)


def _build_classifier_context(session: SessionMemory) -> dict:
    active_cards = _get_context_cards(session)
    recommended_cards = session.user_profile.get("recommended_cards") or []
    if not isinstance(recommended_cards, list):
        recommended_cards = []
    verdicts = session.user_profile.get("last_eligibility_verdicts") or []
    if not isinstance(verdicts, list):
        verdicts = []

    return {
        "active_cards": active_cards,
        "recommended_cards": recommended_cards,
        "active_banking_type": session.user_profile.get("active_banking_type", ""),
        "last_intent": session.get_last_intent() or "",
        "eligibility_cards": [item.get("card_name", "") for item in verdicts if isinstance(item, dict) and item.get("card_name")],
        "known_profile": {
            "monthly_income": session.user_profile.get("monthly_income"),
            "employment_type": session.user_profile.get("employment_type"),
            "age": session.user_profile.get("age"),
        },
    }


def _ground_classifier_output(
    user_message: str,
    history: str,
    session: SessionMemory,
    classifier_output: dict,
) -> dict:
    target_card = classifier_output.get("target_card", "").strip()
    candidate_cards = []
    if target_card:
        resolved_target = compliance_faq.extract_target_card(target_card, "")
        if resolved_target:
            target_card = resolved_target
        else:
            candidate_cards = compliance_faq.resolve_card_candidates(target_card, "", limit=3)
            if len(candidate_cards) == 1:
                target_card = candidate_cards[0]
            else:
                target_card = ""
    if not target_card and classifier_output.get("intent") in {"product_details", "eligibility_check", "how_to_apply"}:
        target_card = compliance_faq.extract_target_card(user_message, history)
        if not target_card:
            context_cards = _get_context_cards(session)
            if len(context_cards) == 1:
                target_card = context_cards[0]
            else:
                candidate_cards = compliance_faq.resolve_card_candidates(user_message, history, limit=3)

    if target_card:
        classifier_output["target_card"] = target_card
        classifier_output["active_cards"] = [target_card]
        classifier_output["needs_preference_form"] = False
        if not classifier_output.get("search_query") or classifier_output.get("search_query") == user_message:
            classifier_output["search_query"] = target_card
    elif candidate_cards:
        classifier_output["candidate_cards"] = candidate_cards

    active_cards = classifier_output.get("active_cards") or []
    if active_cards and classifier_output.get("banking_type") == "both":
        classifier_output["banking_type"] = session.user_profile.get("active_banking_type", "both") or "both"

    return classifier_output


def _stream_or_chunk(
    user_message: str,
    session: SessionMemory,
    stream_fn,
    fallback_fn,
    *args,
) -> Generator[str, None, None]:
    collected: list[str] = []

    if stream_fn:
        for token in stream_fn(*args):
            collected.append(token)
            yield token

    full_response = "".join(collected)
    if not full_response.strip() and fallback_fn:
        full_response = fallback_fn(*args)
        for token in _stream_text(_guardrails(full_response)):
            collected.append(token)
            yield token

    clean = _guardrails("".join(collected) if collected else full_response)
    session.add(user_message, clean)


def _direct_response(intent: str) -> str:
    if intent == "greeting":
        return (
            "Hello! I can help with Prime Bank credit cards, card comparisons, eligibility checks, "
            "applications, and existing cardholder services."
        )
    if intent == "off_topic":
        return (
            "I’m Prime Bank’s credit card assistant, so I can help with credit cards, eligibility, "
            "fees, rewards, applications, and cardholder services."
        )
    return ""


def _clarify_candidate_cards(intent: str, candidate_cards: list[str]) -> str:
    if len(candidate_cards) < 2:
        return ""
    if intent == "eligibility_check":
        return "I found a few matching cards. Tell me which one you want to check eligibility for: " + ", ".join(candidate_cards) + "."
    if intent == "how_to_apply":
        return "I found a few matching cards. Tell me which one you want application steps for: " + ", ".join(candidate_cards) + "."
    if intent == "product_details":
        return "I found a few matching cards. Tell me which one you want details about: " + ", ".join(candidate_cards) + "."
    return ""


def build_crew_stream(
    user_message: str,
    session: SessionMemory,
    request_id: str | None = None,
) -> Generator[str, None, None]:
    started = time.perf_counter()
    session_id = session.session_id
    history = session.get_history_str(max_chars=1000)
    classifier_context = _build_classifier_context(session)
    classifier_output = classify(user_message, history, classifier_context)
    classifier_output = _ground_classifier_output(user_message, history, session, classifier_output)

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

    if classifier_output.get("needs_preference_form"):
        yield _build_preference_form_signal(user_message, session, classifier_output)
        yield json.dumps({"__done_signal__": True, "intent": "", "calculator": ""})
        return

    if classifier_output.get("needs_eligibility_form"):
        yield _build_eligibility_form_signal(user_message, session)
        yield json.dumps({"__done_signal__": True, "intent": "", "calculator": ""})
        return

    clarify = _clarify_candidate_cards(intent, classifier_output.get("candidate_cards") or [])
    if clarify:
        clean = _guardrails(clarify)
        session.add(user_message, clean)
        for token in _stream_text(clean):
            yield token
        yield json.dumps({"__done_signal__": True, "intent": intent, "calculator": calculator_type})
        return

    direct = _direct_response(intent)
    if direct:
        clean = _guardrails(direct)
        session.add(user_message, clean)
        for token in _stream_text(clean):
            yield token
        yield json.dumps({"__done_signal__": True, "intent": intent, "calculator": calculator_type})
        return

    routing = _build_routing(user_message, classifier_output)
    yield "Let me check that for you.\n\n"

    if intent == "catalog_query":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="catalog")
        yield from _stream_or_chunk(
            user_message,
            session,
            getattr(compliance_faq, "run_catalog_stream", None),
            compliance_faq.run_catalog,
            user_message,
            session,
        )
    elif intent == "comparison":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="comparator")
        yield from _stream_or_chunk(
            user_message,
            session,
            getattr(comparator, "run_stream", None),
            comparator.run,
            user_message,
            routing,
            session,
        )
    elif intent == "how_to_apply":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="how_to_apply")
        yield from _stream_or_chunk(
            user_message,
            session,
            getattr(compliance_faq, "run_apply_stream", None),
            compliance_faq.run_apply,
            user_message,
            routing,
            session,
        )
    elif intent == "product_details":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="product_details")
        yield from _stream_or_chunk(
            user_message,
            session,
            getattr(product_advisor, "run_details_stream", None),
            product_advisor.run_details,
            user_message,
            routing,
            session,
        )
    elif intent == "existing_cardholder":
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="cardholder_service")
        yield from _stream_or_chunk(
            user_message,
            session,
            getattr(cardholder_svc, "run_stream", None),
            cardholder_svc.run,
            user_message,
            routing,
            session,
        )
    else:
        log_event("specialist_start", request_id=request_id, session_id=session_id, specialist="faq_compliance")
        yield from _stream_or_chunk(
            user_message,
            session,
            getattr(compliance_faq, "run_faq_stream", None),
            compliance_faq.run_faq,
            user_message,
            routing,
            session,
        )

    mentioned_cards = compliance_faq.extract_recommended_card_names(session.get_last_assistant_response())
    if mentioned_cards:
        _remember_active_cards(session, mentioned_cards, routing.get("banking_type", ""))
    session.set_last_intent(intent)

    yield json.dumps({"__done_signal__": True, "intent": intent, "calculator": calculator_type})
    log_event(
        "pipeline_complete_stream",
        request_id=request_id,
        session_id=session_id,
        intent=intent,
        response_chars=len(session.get_last_assistant_response()),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


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

    session.add(_form_data_summary(form_data), "")

    draft = compliance_faq.run_eligibility(form_data, session)
    clean = _guardrails(draft)

    clean_lower = clean.lower()
    if "❌" in clean or "likely ineligible" in clean_lower or "not eligible" in clean_lower or "ineligible" in clean_lower:
        clean += "\n\nWould you like to explore other cards that may suit your profile? Call **16218** or visit a branch for personalised advice."
    elif "⚠️" in clean or "conditional" in clean_lower or "borderline" in clean_lower:
        clean += "\n\nFor guidance on meeting the remaining requirements, call **16218** or visit a Prime Bank branch."
    elif "✅" in clean or "likely eligible" in clean_lower:
        clean += "\n\n**Ready to apply?** Visit any Prime Bank branch or call **16218** to start your application today."
    else:
        clean += "\n\nFor further assistance, contact Prime Bank at **16218** or visit any branch."

    session.history[-1]["content"] = clean
    session.history[-1]["content_short"] = session._truncate_for_history(clean)
    target_card = form_data.get("target_card", "")
    recommended_cards = session.user_profile.get("recommended_cards") or []
    if not isinstance(recommended_cards, list):
        recommended_cards = []
    verdicts = compliance_faq.extract_eligibility_verdicts(
        clean,
        target_card=target_card,
        recommended_cards=recommended_cards,
    )
    summary = compliance_faq.build_eligibility_verdict_summary(verdicts)
    session.update_profile("last_eligibility_verdicts", verdicts)
    session.update_profile("last_eligibility_summary", summary)

    active_cards = [item.get("card_name", "") for item in verdicts if item.get("card_name")]
    if not active_cards:
        active_cards = [target_card] if target_card else recommended_cards
    if isinstance(active_cards, list) and active_cards:
        _remember_active_cards(session, active_cards)
    session.set_last_intent("eligibility_check")

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
    recommended_cards = compliance_faq.extract_recommended_card_names(clean)
    session.update_profile("recommended_cards", recommended_cards)
    _remember_active_cards(session, recommended_cards, form_data.get("banking_type", ""))
    clean += "\n\n**Want to check if you qualify?** Just ask me to check your eligibility, or visit any Prime Bank branch to apply."

    session.history[-1]["content"] = clean
    session.history[-1]["content_short"] = session._truncate_for_history(clean)

    log_event(
        "preference_form_complete",
        request_id=request_id,
        session_id=session_id,
        response_chars=len(clean),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    session.set_last_intent("i_need_a_credit_card")
    return clean


def clear_preference_session(session_id: str) -> None:
    return

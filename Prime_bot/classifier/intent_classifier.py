import json
import re

from llm.ollama_client import chat


SYSTEM_ROUTE = """Route a Prime Bank credit card chat message.

Return ONLY JSON:
{"category":"new_card"|"existing_card"|"general"|"off_topic","sub_intent":"catalog"|"discover"|"compare"|"eligibility"|"apply"|"details"|"existing_card"|"faq"|"greeting","banking_type":"conventional"|"islami"|"both","confidence":0.0,"calculator":"","search_query":"","target_card":"","use_context_cards":false,"needs_preference_form":false,"needs_eligibility_form":false}

Rules:
- existing_card = cardholder service issues like lost card, blocked card, PIN, statement, bill payment, activation, rewards redemption, dispute, limit increase, supplementary card, or EMI conversion
- general/greeting = greeting or short conversational opener
- off_topic = clearly unrelated to banking, cards, or the current conversation
- new_card = browsing cards, wanting a card, recommendations, comparison, eligibility, details, benefits, fees, rewards, or application
- catalog = browsing available cards
- discover = wants a recommendation or says they want/open/need/get a credit card
- compare = compares two or more cards
- eligibility = asks if they qualify or are eligible
- apply = asks about process, documents, or how to apply
- details = asks about one specific card
- faq = other on-topic credit-card questions
- banking_type = islami for islamic/halal/hasanah/shariah, conventional for explicit conventional, else both
- calculator = emi or rewards only for explicit calculations
- search_query must be short and retrieval-friendly
- Use conversation context and session context when provided
- target_card must be the exact full card name only when the current user message clearly indicates one specific card
- use_context_cards = true when the user is continuing a discussion about cards already in session context and the current message should be grounded in those cards
- needs_preference_form = true only when the user wants a recommendation/discovery flow and a form should be shown
- needs_eligibility_form = true only when the user wants eligibility assessment and a form should be shown
- If the user asks follow-ups like fees, comparison, eligibility, application, or details for already-discussed cards, prefer using session-context cards instead of restarting discovery
- If the user mentions a specific card after a prior conversation, route to details/apply/eligibility for that card rather than showing the discovery form
- Output JSON only

Examples:
"What credit cards do you offer?" -> {"category":"new_card","sub_intent":"catalog","banking_type":"both","confidence":0.97,"calculator":"","search_query":"credit cards offered","target_card":"","use_context_cards":false,"needs_preference_form":false,"needs_eligibility_form":false}
"I need a halal credit card" -> {"category":"new_card","sub_intent":"discover","banking_type":"islami","confidence":0.98,"calculator":"","search_query":"halal credit card recommendation","target_card":"","use_context_cards":false,"needs_preference_form":true,"needs_eligibility_form":false}
"Check my eligibility" with session cards already known -> {"category":"new_card","sub_intent":"eligibility","banking_type":"conventional","confidence":0.96,"calculator":"","search_query":"eligibility for current shortlisted cards","target_card":"","use_context_cards":true,"needs_preference_form":false,"needs_eligibility_form":true}
"Explain the fees" after a comparison of two cards -> {"category":"new_card","sub_intent":"compare","banking_type":"conventional","confidence":0.94,"calculator":"","search_query":"annual fee fee waiver charges for current comparison cards","target_card":"","use_context_cards":true,"needs_preference_form":false,"needs_eligibility_form":false}
"I lost my card" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.98,"calculator":"","search_query":"lost card support","target_card":"","use_context_cards":false,"needs_preference_form":false,"needs_eligibility_form":false}"""

RECOVERY_ROUTE_SYSTEM = """Route the user's latest Prime Bank credit card message.

Return ONLY JSON:
{"category":"new_card"|"existing_card"|"general"|"off_topic","sub_intent":"catalog"|"discover"|"compare"|"eligibility"|"apply"|"details"|"existing_card"|"faq"|"greeting","banking_type":"conventional"|"islami"|"both","confidence":0.0,"calculator":"","search_query":"","target_card":"","use_context_cards":false,"needs_preference_form":false,"needs_eligibility_form":false}

Use the provided history and session context.
If the latest message depends on already discussed cards, set use_context_cards to true.
If the user wants a recommendation, set sub_intent to discover.
If the user wants eligibility, set sub_intent to eligibility.
If the user asks about an existing cardholder service issue, set category to existing_card.
Output JSON only."""

VALID_INTENTS = {
    "greeting",
    "off_topic",
    "catalog_query",
    "i_need_a_credit_card",
    "eligibility_check",
    "comparison",
    "how_to_apply",
    "product_details",
    "existing_cardholder",
    "faq",
}
VALID_BANKING = {"conventional", "islami", "both"}
VALID_CALCULATORS = {"", "emi", "rewards"}
VALID_ENTRY = {"new_card", "existing_card", "general", "off_topic"}
VALID_SUB = {"catalog", "discover", "compare", "eligibility", "apply", "details", "existing_card", "faq", "greeting"}
INTENT_MAP = {
    "catalog": "catalog_query",
    "discover": "i_need_a_credit_card",
    "compare": "comparison",
    "eligibility": "eligibility_check",
    "apply": "how_to_apply",
    "details": "product_details",
    "existing_card": "existing_cardholder",
    "faq": "faq",
    "greeting": "greeting",
}


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text or "").strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def _normalize_route(route: dict, user_message: str, context: dict | None = None) -> dict:
    context = context or {}
    category = route.get("category", "general")
    if category not in VALID_ENTRY:
        category = "general"

    sub_intent = route.get("sub_intent", "faq")
    if sub_intent not in VALID_SUB:
        sub_intent = "faq"
    if category == "existing_card":
        sub_intent = "existing_card"
    if category == "general":
        sub_intent = "greeting" if sub_intent == "greeting" else "faq"
    if category == "off_topic":
        intent = "off_topic"
    else:
        intent = INTENT_MAP.get(sub_intent, "faq")

    banking_type = route.get("banking_type", "both")
    if banking_type not in VALID_BANKING:
        banking_type = "both"

    calculator_type = route.get("calculator", "")
    if calculator_type not in VALID_CALCULATORS:
        calculator_type = ""

    search_query = str(route.get("search_query") or user_message).strip()
    if not search_query:
        search_query = user_message

    try:
        confidence = float(route.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    target_card = str(route.get("target_card") or "").strip()
    use_context_cards = _as_bool(route.get("use_context_cards"))
    context_cards = context.get("active_cards") or []
    if not isinstance(context_cards, list):
        context_cards = []
    active_cards = []
    if target_card:
        active_cards = [target_card]
    elif use_context_cards and context_cards:
        active_cards = context_cards
        if search_query == user_message:
            search_query = " ".join(context_cards + [user_message]).strip()

    needs_preference_form = _as_bool(route.get("needs_preference_form"))
    needs_eligibility_form = _as_bool(route.get("needs_eligibility_form"))

    if intent == "i_need_a_credit_card" and not target_card and not use_context_cards:
        needs_preference_form = needs_preference_form or True
    else:
        needs_preference_form = False

    if intent == "eligibility_check":
        needs_eligibility_form = needs_eligibility_form or True
    else:
        needs_eligibility_form = False

    return {
        "intent": intent,
        "banking_type": banking_type,
        "needs_preference_form": needs_preference_form,
        "needs_eligibility_form": needs_eligibility_form,
        "intent_score": confidence,
        "banking_score": confidence,
        "all_intent_scores": {},
        "calculator_type": calculator_type,
        "search_query": search_query,
        "target_card": target_card,
        "use_context_cards": use_context_cards,
        "active_cards": active_cards,
    }


def _route_prompt(user_message: str, history: str, context: dict | None = None) -> str:
    context_json = json.dumps(context or {}, ensure_ascii=True)
    return (
        f"Conversation history:\n{history or 'None'}\n\n"
        f"Session context JSON:\n{context_json}\n\n"
        f"Current user message:\n{user_message}"
    )


def _recovery_route_prompt(user_message: str, history: str, context: dict | None = None) -> str:
    context_json = json.dumps(context or {}, ensure_ascii=True)
    return (
        f"Session context JSON:\n{context_json}\n\n"
        f"Recent conversation:\n{history or 'None'}\n\n"
        f"Latest user message:\n{user_message}"
    )


def _parse_partial_route_json(text: str) -> dict:
    cleaned = (text or "").strip()
    if not cleaned:
        return {}

    extracted = {}
    patterns = {
        "category": r'"category"\s*:\s*"([^"]+)',
        "sub_intent": r'"sub_intent"\s*:\s*"([^"]+)',
        "banking_type": r'"banking_type"\s*:\s*"([^"]+)',
        "calculator": r'"calculator"\s*:\s*"([^"]*)',
        "search_query": r'"search_query"\s*:\s*"([^"]*)',
        "target_card": r'"target_card"\s*:\s*"([^"]*)',
        "use_context_cards": r'"use_context_cards"\s*:\s*(true|false)',
        "needs_preference_form": r'"needs_preference_form"\s*:\s*(true|false)',
        "needs_eligibility_form": r'"needs_eligibility_form"\s*:\s*(true|false)',
        "confidence": r'"confidence"\s*:\s*([0-9.]+)',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, cleaned)
        if match:
            extracted[key] = match.group(1).strip()
    return extracted


def _route_once(prompt: str, system: str, max_tokens: int) -> tuple[dict, str]:
    raw = chat(
        messages=[{"role": "user", "content": prompt}],
        system=system,
        temperature=0.0,
        max_tokens=max_tokens,
        think=False,
    )
    parsed = _parse_json(raw)
    if not parsed:
        parsed = _parse_partial_route_json(raw)
    return parsed, raw


def _is_actionable_route(route: dict, normalized: dict) -> bool:
    if not route:
        return False
    if normalized.get("intent_score", 0.0) > 0:
        return True
    if normalized.get("intent") not in {"faq", "greeting"}:
        return True
    if normalized.get("target_card"):
        return True
    if normalized.get("use_context_cards"):
        return True
    if normalized.get("needs_preference_form") or normalized.get("needs_eligibility_form"):
        return True
    return False


def classify(user_message: str, history: str = "", context: dict | None = None) -> dict:
    prompt = _route_prompt(user_message, history, context)
    parsed, _ = _route_once(prompt, SYSTEM_ROUTE, 220)
    normalized = _normalize_route(parsed, user_message, context)
    if _is_actionable_route(parsed, normalized):
        return normalized

    parsed, _ = _route_once(prompt, SYSTEM_ROUTE, 220)
    normalized = _normalize_route(parsed, user_message, context)
    if _is_actionable_route(parsed, normalized):
        return normalized

    recovery_prompt = _recovery_route_prompt(user_message, history, context)
    parsed, _ = _route_once(recovery_prompt, RECOVERY_ROUTE_SYSTEM, 160)
    normalized = _normalize_route(parsed, user_message, context)
    return normalized

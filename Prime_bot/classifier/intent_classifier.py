import json
import re

from llm.ollama_client import chat


SYSTEM_ROUTE = """Route a Prime Bank credit card chat message.

Return ONLY JSON:
{"category":"new_card"|"existing_card"|"general"|"off_topic","sub_intent":"catalog"|"discover"|"compare"|"eligibility"|"apply"|"details"|"existing_card"|"faq"|"greeting","banking_type":"conventional"|"islami"|"both","confidence":0.0,"calculator":"","search_query":""}

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
- Use conversation context when provided
- Output JSON only

Examples:
"What credit cards do you offer?" -> {"category":"new_card","sub_intent":"catalog","banking_type":"both","confidence":0.97,"calculator":"","search_query":"credit cards offered"}
"I need a halal credit card" -> {"category":"new_card","sub_intent":"discover","banking_type":"islami","confidence":0.98,"calculator":"","search_query":"halal credit card recommendation"}
"I lost my card" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.98,"calculator":"","search_query":"lost card support"}"""

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


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text or "").strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def _normalize_route(route: dict, user_message: str) -> dict:
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

    needs_preference_form = intent == "i_need_a_credit_card"
    needs_eligibility_form = intent == "eligibility_check"

    if intent != "i_need_a_credit_card":
        needs_preference_form = False
    if intent != "eligibility_check":
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
    }


def _route_prompt(user_message: str, history: str) -> str:
    return (
        f"Conversation history:\n{history or 'None'}\n\n"
        f"Current user message:\n{user_message}"
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


def classify(user_message: str, history: str = "") -> dict:
    prompt = _route_prompt(user_message, history)
    parsed, raw = _route_once(prompt, SYSTEM_ROUTE, 400)

    if not parsed:
        parsed, raw = _route_once(prompt, SYSTEM_ROUTE, 400)

    return _normalize_route(parsed, user_message)

import json
import re
from llm.ollama_client import chat


SYSTEM_ENTRY = """Classify this banking query into ONE category.

Categories:
- new_card: wants a credit card, thinking about getting one, wants to know about cards, wants recommendations
- existing_card: already has a card, needs help with lost/stolen/billing/rewards/PIN/activation/statements

Respond ONLY with JSON: {"category": "new_card" or "existing_card"}"""


SYSTEM_NEW_CARD = """The user is interested in getting a new credit card. Classify their specific need.

Categories:
- discover: browsing, exploring options, wants to see available cards, no specific card in mind, stating banking preference, stating use case
- compare: explicitly wants to compare two or more specific named cards
- eligibility: wants to check if they qualify for a specific card, asking about requirements
- apply: wants to know how to apply for a specific card, application process, documents needed
- details: wants detailed information about one specific card

Respond ONLY with JSON: {"sub_intent": "<category>"}"""


SYSTEM_BANKING = """What banking type is the user asking about?

Types:
- conventional: standard banking, visa, mastercard, JCB, gold, platinum, world
- islami: islamic, shariah, halal, hasanah, riba-free, interest-free islamic
- both: unclear or asking about both

Respond ONLY with JSON: {"banking_type": "<type>"}"""


VALID_ENTRY = {"new_card", "existing_card"}
VALID_SUB = {"discover", "compare", "eligibility", "apply", "details"}
VALID_BANKING = {"conventional", "islami", "both"}

INTENT_MAP = {
    "discover": "i_need_a_credit_card",
    "compare": "comparison",
    "eligibility": "eligibility_check",
    "apply": "how_to_apply",
    "details": "product_details",
}


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r'```(?:json)?', '', text).strip()
    match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}


def _llm_classify(message: str, system: str) -> dict:
    result = chat(
        messages=[{"role": "user", "content": message}],
        system=system,
        temperature=0.0,
        max_tokens=300,
    )
    return _parse_json(result)


def classify(user_message: str) -> dict:
    entry = _llm_classify(user_message, SYSTEM_ENTRY)
    category = entry.get("category", "new_card")
    if category not in VALID_ENTRY:
        category = "new_card"

    if category == "existing_card":
        banking = _llm_classify(user_message, SYSTEM_BANKING)
        banking_type = banking.get("banking_type", "both")
        if banking_type not in VALID_BANKING:
            banking_type = "both"
        return {
            "intent": "existing_cardholder",
            "banking_type": banking_type,
            "intent_score": 0.90,
            "banking_score": 0.90,
            "all_intent_scores": {},
        }

    sub = _llm_classify(user_message, SYSTEM_NEW_CARD)
    sub_intent = sub.get("sub_intent", "discover")
    if sub_intent not in VALID_SUB:
        sub_intent = "discover"

    banking = _llm_classify(user_message, SYSTEM_BANKING)
    banking_type = banking.get("banking_type", "both")
    if banking_type not in VALID_BANKING:
        banking_type = "both"

    return {
        "intent": INTENT_MAP[sub_intent],
        "banking_type": banking_type,
        "intent_score": 0.90,
        "banking_score": 0.90,
        "all_intent_scores": {},
    }
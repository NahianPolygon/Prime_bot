import json
import re
from llm.ollama_client import chat


SYSTEM_ROUTE = """You route messages for a Prime Bank credit card assistant.

Return ONLY JSON with this schema:
{"category":"new_card"|"existing_card","sub_intent":"catalog"|"discover"|"compare"|"eligibility"|"apply"|"details"|"existing_card","banking_type":"conventional"|"islami"|"both"}

Meaning:
- category=new_card for browsing, recommendations, comparisons, eligibility, application help, card details, or general new-card questions
- category=existing_card for cardholder support such as billing, statements, activation, PIN, rewards redemption, lost/stolen card, limit increase, EMI conversion, or service issues
- sub_intent=catalog when the user wants to see available cards or browse the lineup
- sub_intent=discover when the user wants recommendations based on needs, lifestyle, or preferences
- sub_intent=compare when the user wants to compare cards
- sub_intent=eligibility when the user wants to check qualification or requirements
- sub_intent=apply when the user wants application steps, documents, or process
- sub_intent=details when the user wants information about one specific card
- sub_intent=existing_card only when category=existing_card
- banking_type=islami for Islamic, Shariah-compliant, halal, Hasanah, or riba-free requests
- banking_type=conventional for standard non-Islamic cards
- banking_type=both when unclear, mixed, or not specified

Use the conversation context if provided. Infer semantically. Do not explain anything outside the JSON."""


VALID_ENTRY = {"new_card", "existing_card"}
VALID_SUB = {"catalog", "discover", "compare", "eligibility", "apply", "details", "existing_card"}
VALID_BANKING = {"conventional", "islami", "both"}

INTENT_MAP = {
    "catalog": "catalog_query",
    "discover": "i_need_a_credit_card",
    "compare": "comparison",
    "eligibility": "eligibility_check",
    "apply": "how_to_apply",
    "details": "product_details",
    "existing_card": "existing_cardholder",
}


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {}
    return {}


def classify(user_message: str, history: str = "") -> dict:
    if history:
        context_msg = f"""Recent conversation:
{history}

Current message: {user_message}"""
    else:
        context_msg = user_message

    parsed = _parse_json(
        chat(
            messages=[{"role": "user", "content": context_msg}],
            system=SYSTEM_ROUTE,
            temperature=0.0,
            max_tokens=220,
        )
    )

    category = parsed.get("category", "new_card")
    if category not in VALID_ENTRY:
        category = "new_card"

    sub_intent = parsed.get("sub_intent", "discover")
    if category == "existing_card":
        sub_intent = "existing_card"
    elif sub_intent not in VALID_SUB:
        sub_intent = "discover"

    banking_type = parsed.get("banking_type", "both")
    if banking_type not in VALID_BANKING:
        banking_type = "both"

    return {
        "intent": INTENT_MAP[sub_intent],
        "banking_type": banking_type,
        "intent_score": 0.90,
        "banking_score": 0.90,
        "all_intent_scores": {},
    }

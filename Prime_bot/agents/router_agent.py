from llm.ollama_client import chat
from memory.session_memory import SessionMemory

SYSTEM = """You are a banking query router for Prime Bank Bangladesh.
You receive a user message and a pre-classified intent + banking type from a semantic classifier.
Your job is to CONFIRM or OVERRIDE the routing if the classification seems wrong.

Rules:
- If the user mentions "halal", "shariah", "riba", "ujrah", "hasanah", "Islamic" -> banking_type = islami
- If the user asks to compare two or more cards -> intent = comparison
- If the user asks how many cards / lists of products -> intent = catalog_query
- If the user asks about eligibility / qualification / can I apply -> intent = eligibility_check
- If the user mentions lost card / block / stolen / activate / bill payment -> intent = existing_cardholder
- If the user wants a new card / recommendations / which card is best -> intent = i_need_a_credit_card
- If the user asks about fees / charges / documents / application process -> intent = faq_compliance

Respond ONLY with a valid JSON object, no explanation:
{"intent": "<intent>", "banking_type": "<conventional|islami>", "collection": "<collection_name>", "search_query": "<refined search query>"}

Valid intents: i_need_a_credit_card, existing_cardholder, comparison, eligibility_check, catalog_query, faq_compliance
Valid collections: conventional_credit_i_need_a_credit_card, conventional_credit_existing_cardholder,
                   islami_credit_i_need_a_credit_card, islami_credit_existing_cardholder, all_products
"""


def run(
    user_message: str,
    classifier_output: dict,
    session: SessionMemory,
) -> dict:
    import json
    import re

    history = session.get_history_str(max_chars=1500)
    intent = classifier_output["intent"]
    banking = classifier_output["banking_type"]
    i_score = classifier_output["intent_score"]
    b_score = classifier_output["banking_score"]

    prompt = f"""Conversation history:
{history}

User message: \"{user_message}\"

Semantic classifier pre-classified as:
- intent: {intent} (confidence: {i_score:.2f})
- banking_type: {banking} (confidence: {b_score:.2f})

Confirm or correct this routing. Return JSON only."""

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.0,
    )

    try:
        match = re.search(r"\{[^{}]+\}", response, re.DOTALL)
        if match:
            routing = json.loads(match.group())
            for key in ("intent", "banking_type", "collection", "search_query"):
                if key not in routing:
                    raise ValueError(f"Missing key: {key}")
            return routing
    except Exception:
        pass

    collection = f"{banking}_credit_{intent}" if intent in (
        "i_need_a_credit_card",
        "existing_cardholder",
    ) else "all_products"

    return {
        "intent": intent,
        "banking_type": banking,
        "collection": collection,
        "search_query": user_message,
    }

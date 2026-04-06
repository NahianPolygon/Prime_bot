import json
import re
from llm.ollama_client import chat
from memory.session_memory import SessionMemory


FOLLOWUP_SYSTEM = """You decide whether a user's new message is a FOLLOW-UP to the previous conversation topic or a completely NEW topic.

A message is a FOLLOW-UP if:
- It refers to cards, options, or information from the previous exchange
- It asks for a recommendation, preference, or opinion based on what was just discussed
- It asks "which one", "what about", "tell me more", "best for me", etc. in context of the previous response
- It adds personal details (income, lifestyle, preferences) to refine the previous answer
- It would not make sense without reading the previous conversation

A message is a NEW topic if:
- It introduces a completely different subject unrelated to the previous exchange
- It asks about something never mentioned before with no reference to prior context
- It could stand entirely on its own without any prior conversation

Respond ONLY with JSON: {"is_followup": true} or {"is_followup": false}"""


def _is_followup(user_message: str, session: SessionMemory) -> bool:
    if not session.get_last_intent():
        return False

    history = session.get_history_str(max_chars=800)
    if not history.strip():
        return False

    prompt = f"""Previous conversation:
{history}

New message from user: "{user_message}"

Is this new message a follow-up to the previous conversation or a completely new topic?"""

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system=FOLLOWUP_SYSTEM,
        temperature=0.0,
        max_tokens=50,
    )

    try:
        cleaned = re.sub(r'```(?:json)?', '', result).strip()
        match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            return parsed.get("is_followup", False)
    except Exception:
        pass

    return False


def run(
    user_message: str,
    classifier_output: dict,
    session: SessionMemory,
) -> dict:
    intent = classifier_output["intent"]
    banking = classifier_output["banking_type"]

    last_intent = session.get_last_intent()

    if last_intent and last_intent != intent and _is_followup(user_message, session):
        intent = last_intent

    session.set_last_intent(intent)

    if banking == "both":
        collection = "all_products"
    elif intent in ("i_need_a_credit_card", "how_to_apply", "product_details"):
        collection = f"{banking}_credit_i_need_a_credit_card"
    elif intent == "existing_cardholder":
        collection = f"{banking}_credit_existing_cardholder"
    else:
        collection = "all_products"

    return {
        "intent": intent,
        "banking_type": banking,
        "collection": collection,
        "search_query": user_message,
    }
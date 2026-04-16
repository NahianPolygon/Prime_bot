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

_FOLLOWUP_KEYWORDS = frozenset([
    "which one", "that one", "the first", "the second", "the third",
    "tell me more", "more details", "what about", "how about",
    "compared to", "vs", "versus", "better", "best for me",
    "and the", "also", "what else", "any other", "difference between",
    "recommend", "suggest", "prefer", "sounds good", "i like", "i want that",
    "ok", "okay", "sure", "yes", "no", "go ahead", "proceed",
    "this one", "that card", "the card", "it", "its", "this card",
])

_NEW_TOPIC_KEYWORDS = frozenset([
    "i lost", "i want to apply", "i need to pay", "my bill", "my pin",
    "how do i", "what is", "what are", "how much", "tell me about",
])


def _fast_followup_check(user_message: str) -> bool | None:
    msg_lower = user_message.lower().strip()

    if len(msg_lower.split()) <= 6:
        if any(kw in msg_lower for kw in _FOLLOWUP_KEYWORDS):
            return True

    if any(kw in msg_lower for kw in _NEW_TOPIC_KEYWORDS):
        return False

    return None


def _is_followup(user_message: str, session: SessionMemory) -> bool:
    if not session.get_last_intent():
        return False

    history = session.get_history_str(max_chars=800)
    if not history.strip():
        return False

    fast_result = _fast_followup_check(user_message)
    if fast_result is not None:
        return fast_result

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
            return bool(parsed.get("is_followup", False))
    except Exception:
        pass

    return False


def _resolve_collection(intent: str, banking: str) -> str:
    if banking == "both":
        return "all_products"
    if intent in ("i_need_a_credit_card", "how_to_apply", "product_details"):
        return f"{banking}_credit_i_need_a_credit_card"
    if intent == "existing_cardholder":
        return f"{banking}_credit_existing_cardholder"
    return "all_products"


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

    collection = _resolve_collection(intent, banking)

    return {
        "intent": intent,
        "banking_type": banking,
        "collection": collection,
        "search_query": user_message,
    }
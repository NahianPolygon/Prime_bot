from tools.rag_tool import rag_search_multi
from llm.ollama_client import chat
from memory.session_memory import SessionMemory
import re

SYSTEM = """You are the Prime Bank Cardholder Services specialist.
You help existing credit card holders using ONLY the knowledge base chunks provided.

You handle: lost/stolen card, card activation, bill payment, statements, balance queries, reward points, credit limit increase, EMI conversion, PIN reset, supplementary cards.

You MUST:
- For ANY lost/stolen/block emergency, put "Call 16218 IMMEDIATELY" as the FIRST line
- Use ONLY information from the provided chunks
- Give clear step-by-step instructions when applicable
- Be concise and action-oriented
- Always use the actual card name not internal codes

You MUST NOT:
- Invent any policy, fee, process, or phone number not in the chunks
- Give vague answers when chunks contain specific details
- Display product_id, internal IDs, or system codes like CARD_001 or ISLAMI_CARD_001

If the query is not covered in chunks, say: "Please call 16218 or visit your nearest Prime Bank branch."
"""

_EMERGENCY_KEYWORDS = frozenset([
    "lost", "stolen", "missing", "block", "blocked", "unauthorized",
    "fraud", "fraudulent", "someone used", "not me", "compromised",
    "theft", "lost my card", "cant find my card",
])

_INTENT_SEARCH_MAP = {
    "activat": "activate card new card how to activate",
    "pin": "PIN setup reset generate PIN MyPrime",
    "bill": "bill payment pay dues outstanding balance MyPrime internet banking",
    "statement": "transaction history statement balance inquiry",
    "reward": "reward points redeem points balance points expiry",
    "limit": "credit limit increase request limit enhancement",
    "emi": "EMI conversion installment 0 percent interest",
    "supplement": "supplementary card add family member",
    "endorse": "endorsement foreign currency passport branch",
    "damage": "damaged card replacement branch visit",
}


def _clean_context(context: str) -> str:
    context = re.sub(r'product_id:\s*\S+', '', context)
    context = re.sub(r'\b(?:CARD|ISLAMI_CARD)_\d+\b', '', context)
    context = re.sub(r'\n\s*\n\s*\n', '\n\n', context)
    return context.strip()


def _get_intent_search_query(message: str) -> str:
    msg = message.lower()
    for keyword, search_terms in _INTENT_SEARCH_MAP.items():
        if keyword in msg:
            return search_terms
    return message


def _is_emergency(message: str) -> bool:
    msg = message.lower()
    return any(kw in msg for kw in _EMERGENCY_KEYWORDS)


def _get_collections(banking: str) -> list[str]:
    if banking == "both":
        return [
            "conventional_credit_existing_cardholder",
            "islami_credit_existing_cardholder",
            "conventional_credit_i_need_a_credit_card",
            "islami_credit_i_need_a_credit_card",
        ]
    return [
        f"{banking}_credit_existing_cardholder",
        f"{banking}_credit_i_need_a_credit_card",
    ]


def run(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    collections = _get_collections(banking)

    if _is_emergency(user_message):
        context = rag_search_multi(
            "lost stolen card block emergency contact 16218",
            collections,
            top_k=4,
        )
        context = _clean_context(context) if not context.startswith("[NO RESULTS]") else ""

        emergency_prompt = f"""KNOWLEDGE BASE CHUNKS:
{context}

Cardholder emergency: {user_message}

The FIRST line of your response MUST be: "🚨 **Call 16218 IMMEDIATELY** to block your card."
Then provide any additional steps from the chunks above."""

        return chat(
            messages=[{"role": "user", "content": emergency_prompt}],
            system=SYSTEM,
            temperature=0.1,
            max_tokens=600,
        )

    search_q = _get_intent_search_query(routing.get("search_query", user_message))
    context = rag_search_multi(search_q, collections, top_k=5)

    if context.startswith("[NO RESULTS]"):
        fallback_context = rag_search_multi(user_message, collections, top_k=4)
        if fallback_context.startswith("[NO RESULTS]"):
            return "Please call **16218** or visit your nearest Prime Bank branch for assistance with your card."
        context = fallback_context

    context = _clean_context(context)
    history = session.get_history_str(max_chars=800)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

Cardholder query: {user_message}

Answer using ONLY the chunks above. Use actual card names, never internal codes. If this is a lost/stolen card emergency, put the helpline number first."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.2,
        max_tokens=2000,
    )
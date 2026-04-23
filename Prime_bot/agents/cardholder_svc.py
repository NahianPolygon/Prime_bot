import re
from typing import Generator

from llm.ollama_client import chat, chat_stream
from memory.session_memory import SessionMemory
from tools.rag_tool import rag_search_multi

SYSTEM = """You are the Prime Bank Cardholder Services specialist.
You help existing credit card holders using ONLY the knowledge base chunks provided.

You handle: lost/stolen card, card activation, bill payment, statements, balance queries, reward points, credit limit increase, EMI conversion, PIN reset, supplementary cards.

You MUST:
- For ANY lost/stolen/block emergency, put "Call 16218 (local) or +88022222222 (international) IMMEDIATELY" as the FIRST line whenever those numbers are present in the chunks
- Use ONLY information from the provided chunks
- Give clear step-by-step instructions when applicable
- Be concise and action-oriented
- Always use the actual card name not internal codes
- When the chunks include phone numbers, preserve them exactly in the answer

You MUST NOT:
- Invent any policy, fee, process, or phone number not in the chunks
- Give vague answers when chunks contain specific details
- Display product_id, internal IDs, or system codes like CARD_001 or ISLAMI_CARD_001

If the query is not covered in chunks, say: "Please call **16218** (local) or **+88022222222** (international) or visit your nearest Prime Bank branch."
"""


def _clean_context(context: str) -> str:
    context = re.sub(r'product_id:\s*\S+', '', context)
    context = re.sub(r'\b(?:CARD|ISLAMI_CARD)_\d+\b', '', context)
    context = re.sub(r'\n\s*\n\s*\n', '\n\n', context)
    return context.strip()


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

    context = rag_search_multi(user_message, collections, top_k=5)

    if context.startswith("[NO RESULTS]"):
        fallback_context = rag_search_multi(user_message, collections + ["all_products"], top_k=4)
        if fallback_context.startswith("[NO RESULTS]"):
            return "Please call **16218** (local) or **+88022222222** (international) or visit your nearest Prime Bank branch for assistance with your card."
        context = fallback_context

    context = _clean_context(context)
    history = session.get_history_str(max_chars=800)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

Cardholder query: {user_message}

Answer using ONLY the chunks above. Use actual card names, never internal codes. If this is a lost/stolen card emergency, put the local and international helpline numbers first exactly as they appear in the chunks."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.2,
        max_tokens=2000,
        think=False,
    )


def run_stream(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> Generator[str, None, None]:
    banking = routing["banking_type"]
    collections = _get_collections(banking)

    context = rag_search_multi(user_message, collections, top_k=5)
    if context.startswith("[NO RESULTS]"):
        fallback_context = rag_search_multi(user_message, collections + ["all_products"], top_k=4)
        if fallback_context.startswith("[NO RESULTS]"):
            yield "Please call **16218** (local) or **+88022222222** (international) or visit your nearest Prime Bank branch for assistance with your card."
            return
        context = fallback_context

    context = _clean_context(context)
    history = session.get_history_str(max_chars=800)
    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

Cardholder query: {user_message}

Answer using ONLY the chunks above. Use actual card names, never internal codes. If this is a lost/stolen card emergency, put the local and international helpline numbers first exactly as they appear in the chunks."""

    for token in chat_stream(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.2,
        max_tokens=2000,
        think=False,
    ):
        yield token

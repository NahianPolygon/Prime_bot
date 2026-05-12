import re
from typing import Generator

from kb_config import get_all_products_collection
from llm.ollama_client import chat, chat_stream
from memory.session_memory import SessionMemory
from tools.rag_tool import rag_search_multi, rag_search_multi_queries
from agents.compliance.common import get_collections

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
- When the chunks include multiple payment methods, reporting channels, links, or service options, include the clearly listed options instead of giving only one example

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
        return get_collections("both", "existing_cardholder") + get_collections("both", "i_need_a_credit_card")
    return get_collections(banking, "existing_cardholder") + get_collections(banking, "i_need_a_credit_card")


def _build_context(user_message: str, routing: dict) -> str:
    banking = routing["banking_type"]
    collections = _get_collections(banking)
    active_cards = routing.get("active_cards") or []
    target_card = (routing.get("target_card") or "").strip()
    focus = [target_card] if target_card else [card for card in active_cards if isinstance(card, str) and card.strip()]
    search_q = routing.get("search_query", user_message)
    if focus:
        search_q = " ".join(focus + [search_q]).strip()

    queries = [
        search_q,
        f"{search_q} cardholder services bill payment dispute lost card activation pin limit transaction history",
        f"{search_q} contact center branch internet banking myprime standing instruction auto debit",
        f"{search_q} report stolen lost damaged card dispute process faq terms conditions",
    ]
    queries.extend(f"{card} {user_message}" for card in focus)

    context = rag_search_multi_queries(
        queries,
        collections + [get_all_products_collection()],
        top_k_per_query=3,
        max_context_chars=9000,
    )

    if context.startswith("[NO RESULTS]"):
        context = rag_search_multi(search_q, collections + [get_all_products_collection()], top_k=6)
    return context


def run(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    context = _build_context(user_message, routing)
    if context.startswith("[NO RESULTS]"):
        return "Please call **16218** (local) or **+88022222222** (international) or visit your nearest Prime Bank branch for assistance with your card."

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
    context = _build_context(user_message, routing)
    if context.startswith("[NO RESULTS]"):
        yield "Please call **16218** (local) or **+88022222222** (international) or visit your nearest Prime Bank branch for assistance with your card."
        return

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

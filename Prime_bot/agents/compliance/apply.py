from typing import Generator

from kb_config import get_all_products_collection
from llm.ollama_client import chat, chat_stream
from memory.session_memory import SessionMemory
from tools.rag_tool import rag_search_multi, rag_search_multi_queries
from .common import clean_context, get_collections

APPLY_SYSTEM = """You are the Prime Bank Application Guide.

You MUST:
- Explain the application process using ONLY the knowledge base chunks provided
- List required documents from the chunks
- Mention any fees or conditions from the chunks
- When the chunks contain a document list or eligibility list, include the clearly listed items instead of summarizing loosely
- Prefer the specific target card details over generic wording when a card is identified in the chunks

You MUST NOT:
- Invent any steps, documents, or fees not in the chunks
- Display product_id, internal IDs, or system codes to the user

If information is missing say: "The provided chunks do not include that application detail."
"""


def _build_context(user_message: str, routing: dict) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)
    target_card = (routing.get("target_card") or "").strip()
    active_cards = routing.get("active_cards") or []
    focus = [target_card] if target_card else [card for card in active_cards if isinstance(card, str) and card.strip()]
    if focus:
        search_q = " ".join(focus + [search_q]).strip()

    collections = get_collections(banking, "i_need_a_credit_card")
    collections += get_collections(banking, "existing_cardholder")
    collections.append(get_all_products_collection())
    collections = list(dict.fromkeys(collections))

    queries = [
        search_q,
        f"{search_q} application process required documents eligibility how to apply",
        f"{search_q} documents required financial documents identity income employment E-TIN",
        f"{search_q} branch submission approval timeline terms conditions schedule of charges",
    ]
    queries.extend(f"{card} {user_message}" for card in focus)

    context = rag_search_multi_queries(
        queries,
        collections,
        top_k_per_query=3,
        max_context_chars=9000,
    )
    if context.startswith("[NO RESULTS]"):
        context = rag_search_multi(search_q, collections, top_k=6)
    if context.startswith("[NO RESULTS]"):
        return context
    return clean_context(context)


def _build_prompt(user_message: str, session: SessionMemory, context: str) -> str:
    history = session.get_history_str(max_chars=1000)
    return f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User question: {user_message}

Answer using ONLY the chunks above.
If the chunks list eligibility requirements, required documents, financial documents, salaried/self-employed requirements, or application steps, include them clearly and separately instead of compressing them into one vague summary.
Do not display any product_id or internal codes."""


def run_apply(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    context = _build_context(user_message, routing)
    if context.startswith("[NO RESULTS]"):
        return "[NO RESULTS]"

    return chat(
        messages=[{"role": "user", "content": _build_prompt(user_message, session, context)}],
        system=APPLY_SYSTEM,
        temperature=0.2,
        max_tokens=2000,
        think=False,
    )


def run_apply_stream(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> Generator[str, None, None]:
    context = _build_context(user_message, routing)
    if context.startswith("[NO RESULTS]"):
        yield "[NO RESULTS]"
        return

    for token in chat_stream(
        messages=[{"role": "user", "content": _build_prompt(user_message, session, context)}],
        system=APPLY_SYSTEM,
        temperature=0.2,
        max_tokens=2000,
        think=False,
    ):
        yield token

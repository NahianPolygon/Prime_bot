import re
from typing import Generator

from kb_config import get_all_products_collection
from agents.compliance.common import get_collections
from llm.ollama_client import chat, chat_stream
from memory.session_memory import SessionMemory
from tools.rag_tool import rag_search_multi, rag_search_multi_queries

SYSTEM = """You are the Prime Bank Credit Card Product Advisor.
You recommend credit cards using ONLY the knowledge base chunks provided below.

You MUST:
- Pick 1-3 cards from the chunks that best match the user's needs
- For each card, list the card name and the most relevant available details from the chunks such as credit limit, reward points, fee waivers, or key benefits
- Quote exact numbers only when they are present in the chunks
- Mention fee waiver conditions if present in chunks
- If both conventional and Islamic cards match, present both options clearly
- Always use the actual card name (e.g. "Visa Gold", "Mastercard Platinum") not internal codes
- End with: "Would you like me to check your eligibility or compare these cards?"

You MUST NOT:
- Mention any card not found in the chunks
- Invent any number, fee, benefit, or policy
- Give a vague answer without specific card details
- Display product_id, internal IDs, or system codes like CARD_001 or ISLAMI_CARD_001

If chunks contain no relevant cards, say: "Please contact Prime Bank at 16218 for assistance."
"""

DETAILS_SYSTEM = """You are the Prime Bank Credit Card Product Specialist.
You provide detailed information about a specific credit card using ONLY the knowledge base chunks.

You MUST:
- Show all available details present in the chunks: card name, credit limit, annual fee, interest rate, reward points, insurance, key benefits, fee waiver conditions, lounge access, EMI options
- Quote exact numbers only when they are present in the chunks
- Use bullet points for lists of 3 or more benefits
- Always use the actual card name (e.g. "Visa Gold", "Mastercard Platinum") not internal codes
- End with: "Would you like to check your eligibility, compare this with another card, or know how to apply?"

You MUST NOT:
- Invent any detail not in the chunks
- Give vague descriptions when chunks have specific numbers
- Display product_id, internal IDs, or system codes like CARD_001 or ISLAMI_CARD_001
- Omit sections that are present in the chunks

If the card is not found in chunks, say: "Please contact Prime Bank at 16218 for details about this card."
"""


def _clean_context(context: str) -> str:
    context = re.sub(r'product_id:\s*\S+', '', context)
    context = re.sub(r'\b(?:CARD|ISLAMI_CARD)_\d+\b', '', context)
    context = re.sub(r'\n\s*\n\s*\n', '\n\n', context)
    return context.strip()


def _get_collections(banking: str) -> list[str]:
    if banking == "both":
        return get_collections("both", "i_need_a_credit_card")
    other = "islami" if banking == "conventional" else "conventional"
    return get_collections(banking, "i_need_a_credit_card") + get_collections(other, "i_need_a_credit_card")


def _fetch_context(search_q: str, collections: list[str], top_k: int = 6) -> str | None:
    context = rag_search_multi(search_q, collections, top_k=top_k)
    if not context.startswith("[NO RESULTS]"):
        return _clean_context(context)

    broader_q = " ".join(search_q.split()[:4]) if len(search_q.split()) > 4 else search_q
    fallback = rag_search_multi(broader_q, collections + [get_all_products_collection()], top_k=top_k)
    if not fallback.startswith("[NO RESULTS]"):
        return _clean_context(fallback)

    return None


def _fetch_expanded_context(
    search_q: str,
    collections: list[str],
    spec_terms: str,
    top_k_per_query: int = 4,
    max_context_chars: int = 7000,
) -> str | None:
    queries = [
        search_q,
        f"{search_q} {spec_terms}",
    ]
    context = rag_search_multi_queries(
        queries,
        collections,
        top_k_per_query=top_k_per_query,
        max_context_chars=max_context_chars,
    )
    if not context.startswith("[NO RESULTS]"):
        return _clean_context(context)
    return None


def run(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)
    collections = _get_collections(banking)

    context = _fetch_expanded_context(
        search_q,
        collections,
        "benefits features reward points lounge insurance fee waiver eligibility",
        top_k_per_query=4,
        max_context_chars=6200,
    ) or _fetch_context(search_q, collections)
    if context is None:
        return "[NO RESULTS]"

    history = session.get_history_str(max_chars=1000)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Using ONLY the chunks above, recommend the most suitable Prime Bank credit card(s). For each card include the card name, the strongest matching benefits, and any exact figures that are actually present in the chunks. Use actual card names, never internal codes. Do not invent any information."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.3,
        max_tokens=2000,
        think=False,
    )


def run_stream(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> Generator[str, None, None]:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)
    collections = _get_collections(banking)

    context = _fetch_expanded_context(
        search_q,
        collections,
        "benefits features reward points lounge insurance fee waiver eligibility",
        top_k_per_query=4,
        max_context_chars=6200,
    ) or _fetch_context(search_q, collections)
    if context is None:
        yield "[NO RESULTS]"
        return

    history = session.get_history_str(max_chars=1000)
    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Using ONLY the chunks above, recommend the most suitable Prime Bank credit card(s). For each card include the card name, the strongest matching benefits, and any exact figures that are actually present in the chunks. Use actual card names, never internal codes. Do not invent any information."""

    for token in chat_stream(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.3,
        max_tokens=2000,
        think=False,
    ):
        yield token


def run_details(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)
    collections = _get_collections(banking)
    collections.append(get_all_products_collection())
    collections = list(dict.fromkeys(collections))

    context = _fetch_expanded_context(
        search_q,
        collections,
        "annual fee fee waiver charges credit limit reward points lounge travel insurance EMI interest-free period eligibility",
        top_k_per_query=5,
        max_context_chars=7600,
    ) or _fetch_context(search_q, collections, top_k=8)
    if context is None:
        return "[NO RESULTS]"

    history = session.get_history_str(max_chars=1000)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Provide ALL available details about the requested card using ONLY the chunks above. Cover every section present in the chunks: credit limit, fees, interest rate, rewards, insurance, lounge access, EMI options, eligibility highlights. Use actual card names, never internal codes. Do not omit any information that is present in the chunks."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=DETAILS_SYSTEM,
        temperature=0.2,
        max_tokens=2500,
        think=False,
    )


def run_details_stream(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> Generator[str, None, None]:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)
    collections = _get_collections(banking)
    collections.append(get_all_products_collection())
    collections = list(dict.fromkeys(collections))

    context = _fetch_expanded_context(
        search_q,
        collections,
        "annual fee fee waiver charges credit limit reward points lounge travel insurance EMI interest-free period eligibility",
        top_k_per_query=5,
        max_context_chars=7600,
    ) or _fetch_context(search_q, collections, top_k=8)
    if context is None:
        yield "[NO RESULTS]"
        return

    history = session.get_history_str(max_chars=1000)
    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Provide ALL available details about the requested card using ONLY the chunks above. Cover every section present in the chunks: credit limit, fees, interest rate, rewards, insurance, lounge access, EMI options, eligibility highlights. Use actual card names, never internal codes. Do not omit any information that is present in the chunks."""

    for token in chat_stream(
        messages=[{"role": "user", "content": prompt}],
        system=DETAILS_SYSTEM,
        temperature=0.2,
        max_tokens=2500,
        think=False,
    ):
        yield token

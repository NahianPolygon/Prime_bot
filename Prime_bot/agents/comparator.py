import re
from typing import Generator

from kb_config import get_all_products_collection
from agents.compliance.common import get_collections
from llm.ollama_client import chat, chat_stream
from memory.session_memory import SessionMemory
from tools.rag_tool import rag_search_multi


SYSTEM = """You are the Prime Bank Credit Card Comparator.

You MUST:
- Use ONLY the provided knowledge base chunks
- Compare only the cards that are supported by the chunks
- Present the answer as a markdown comparison table
- Use actual card names, never internal IDs or system codes
- Use exact figures only when they are present in the chunks
- Use "N/A" when a comparison field is not stated in the chunks
- End with: "Would you like to check your eligibility for any of these cards, or know how to apply?"

Recommended comparison rows:
- Annual fee
- Fee waiver
- Credit limit
- Reward points
- Interest-free period
- Lounge or travel benefits
- Insurance
- Banking type
- Best fit

Do not invent information and do not mention any card that is not grounded in the chunks."""

_SPEC_QUERY = "credit limit annual fee reward points interest-free period insurance fee waiver lounge travel benefits"


def _clean_context(context: str) -> str:
    context = re.sub(r"product_id:\s*\S+", "", context)
    context = re.sub(r"\b(?:CARD|ISLAMI_CARD)_\d+\b", "", context)
    context = re.sub(r"\n\s*\n\s*\n", "\n\n", context)
    return context.strip()


def _build_prompt(user_message: str, session: SessionMemory, context: str) -> str:
    history = session.get_history_str(max_chars=500)
    return f"""KNOWLEDGE BASE CHUNKS (use ONLY these for all comparison data):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Compare the relevant Prime Bank credit cards grounded in the chunks above. Use a markdown table with the most important differences and then add a short "Best fit" summary for each card."""


def _get_context(user_message: str, routing: dict) -> str:
    search_q = routing.get("search_query", user_message)
    active_cards = routing.get("active_cards") or []
    banking_type = routing.get("banking_type", "both")

    if active_cards:
        search_q = " ".join(active_cards + [search_q])

    if banking_type == "conventional":
        collections = get_collections("conventional", "i_need_a_credit_card") + [get_all_products_collection()]
    elif banking_type == "islami":
        collections = get_collections("islami", "i_need_a_credit_card") + [get_all_products_collection()]
    else:
        collections = get_collections("both", "i_need_a_credit_card") + [get_all_products_collection()]

    topic_context = rag_search_multi(search_q, collections, top_k=5, max_context_chars=3200)
    if topic_context.startswith("[NO RESULTS]"):
        return "[NO RESULTS]"

    spec_context = rag_search_multi(_SPEC_QUERY, collections, top_k=4, max_context_chars=1800)
    if spec_context.startswith("[NO RESULTS]"):
        return _clean_context(topic_context)
    return _clean_context(topic_context + "\n\n---\n\n" + spec_context)


def run(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    context = _get_context(user_message, routing)
    if context.startswith("[NO RESULTS]"):
        return "[NO RESULTS]"

    prompt = _build_prompt(user_message, session, context)
    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.1,
        max_tokens=2200,
        think=False,
    )


def run_stream(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> Generator[str, None, None]:
    context = _get_context(user_message, routing)
    if context.startswith("[NO RESULTS]"):
        yield "[NO RESULTS]"
        return

    prompt = _build_prompt(user_message, session, context)
    for token in chat_stream(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.1,
        max_tokens=2200,
        think=False,
    ):
        yield token

from tools.rag_tool import rag_search_multi
from llm.ollama_client import chat
from memory.session_memory import SessionMemory

SYSTEM = """You are the Prime Bank Credit Card Product Advisor.
You recommend credit cards using ONLY the knowledge base chunks provided below.

You MUST:
- Pick 1-3 cards from the chunks that best match the user's needs
- For each card, list: product_id, card name, credit limit, annual fee, reward points, key benefits
- Quote exact numbers from the chunks
- Mention fee waiver conditions if present in chunks
- If both conventional and Islamic cards match, present both options clearly
- End with: "Would you like me to check your eligibility or compare these cards?"

You MUST NOT:
- Mention any card not found in the chunks
- Invent any number, fee, benefit, or policy
- Give a vague answer without specific card details

If chunks contain no relevant cards, say: "Please contact Prime Bank at 16218 for assistance."
"""

DETAILS_SYSTEM = """You are the Prime Bank Credit Card Product Specialist.
You provide detailed information about a specific credit card using ONLY the knowledge base chunks.

You MUST:
- Show all available details: product_id, card name, credit limit, annual fee, interest rate, reward points, insurance, key benefits, fee waiver conditions
- Quote exact numbers from the chunks
- Use bullet points for benefits
- End with: "Would you like to check your eligibility, compare this with another card, or know how to apply?"

You MUST NOT:
- Invent any detail not in the chunks
- Give vague descriptions when chunks have specific numbers

If the card is not found in chunks, say: "Please contact Prime Bank at 16218 for details about this card."
"""


def _get_collections(banking: str) -> list[str]:
    if banking == "both":
        return [
            "conventional_credit_i_need_a_credit_card",
            "islami_credit_i_need_a_credit_card",
        ]
    other = "islami" if banking == "conventional" else "conventional"
    return [
        f"{banking}_credit_i_need_a_credit_card",
        f"{other}_credit_i_need_a_credit_card",
    ]


def run(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = _get_collections(banking)

    context = rag_search_multi(search_q, collections, top_k=6)

    if context.startswith("[NO RESULTS]"):
        return "[NO RESULTS]"

    history = session.get_history_str(max_chars=1000)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Using ONLY the chunks above, recommend the most suitable Prime Bank credit card(s). For each card include the product_id, name, credit limit, annual fee, reward points rate, and top 3 benefits. Do not invent any information."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.3,
        max_tokens=1200,
    )


def run_details(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = _get_collections(banking)
    collections.append("all_products")
    collections = list(dict.fromkeys(collections))

    context = rag_search_multi(search_q, collections, top_k=6)

    if context.startswith("[NO RESULTS]"):
        return "[NO RESULTS]"

    history = session.get_history_str(max_chars=1000)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Provide all available details about the requested card using ONLY the chunks above. Do not invent any information."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=DETAILS_SYSTEM,
        temperature=0.2,
        max_tokens=1200,
    )
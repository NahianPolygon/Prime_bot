from tools.rag_tool import rag_search_multi
from llm.ollama_client import chat
from memory.session_memory import SessionMemory

SYSTEM = """You are the Prime Bank Credit Card Comparator.
You create accurate, structured side-by-side comparisons of credit card products.

Rules:
- ALWAYS use a markdown table for multi-attribute comparisons
- Compare only attributes found in the retrieved knowledge base chunks
- Cite product_id for each card column header (e.g. \"Visa Gold [CARD_001]\")
- Include these rows when available: Credit Limit, Annual Fee, Reward Points, Interest-Free Period,
  Insurance, Special Benefits, Banking Type, Fee Waiver Condition
- After the table, write a 2-3 sentence \"Best For\" summary for each card
- If the user asked \"which is better for me?\" and you know their profile, factor it in
- NEVER fabricate attributes not in the retrieved chunks - leave the cell blank or write \"N/A\"
- End with: \"Would you like to check your eligibility for any of these cards?\"
"""


def run(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    search_q = routing.get("search_query", user_message)

    collections = [
        "conventional_credit_i_need_a_credit_card",
        "islami_credit_i_need_a_credit_card",
        "conventional_credit_existing_cardholder",
        "islami_credit_existing_cardholder",
        "all_products",
    ]
    context = rag_search_multi(search_q, collections, top_k=8)
    history = session.get_history_str()
    profile = session.get_profile_str()

    prompt = f"""Conversation so far:
{history}

User profile (if known):
{profile}

User's comparison request: {user_message}

Retrieved knowledge base:
{context}

Create a detailed side-by-side comparison table. Use markdown formatting."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.2,
    )

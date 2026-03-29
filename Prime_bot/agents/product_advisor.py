from tools.rag_tool import rag_search_multi
from llm.ollama_client import chat
from memory.session_memory import SessionMemory

SYSTEM = """You are the Prime Bank Credit Card Product Advisor.
Your job is to recommend the best credit card(s) for the user based on their needs and preferences.

Rules:
- ONLY recommend cards that appear in the retrieved knowledge base chunks
- Cite the product_id for every card you mention (e.g. CARD_001, ISLAMI_CARD_001)
- If the user hasn't specified conventional or Islamic banking, briefly ask
- Highlight the top 2-3 most relevant features per card based on what the user said
- If a card has a fee waiver condition, always mention it
- End with: \"Would you like me to check your eligibility or compare these cards?\"
- NEVER invent products, limits, fees, or benefits not in the retrieved chunks
- If information is missing, say: \"Please contact Prime Bank at 16218 for details.\"
"""


def run(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = [f"{banking}_credit_i_need_a_credit_card"]
    other = "islami" if banking == "conventional" else "conventional"
    collections.append(f"{other}_credit_i_need_a_credit_card")

    context = rag_search_multi(search_q, collections, top_k=6)
    history = session.get_history_str()

    prompt = f"""Conversation so far:
{history}

User's request: {user_message}

Retrieved knowledge base:
{context}

Recommend the most suitable Prime Bank credit card(s). Cite product_id for each."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.3,
    )

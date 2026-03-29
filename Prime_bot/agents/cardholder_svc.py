from tools.rag_tool import rag_search_multi
from llm.ollama_client import chat
from memory.session_memory import SessionMemory

SYSTEM = """You are the Prime Bank Cardholder Services specialist.
You help existing credit card holders with their queries.

You handle:
- Lost / stolen card -> always direct to 16218 IMMEDIATELY as first step
- Card activation
- Bill payment methods
- Statement and balance queries
- Reward points redemption
- Credit limit increase requests
- EMI conversion on transactions
- PIN reset
- Supplementary card requests

Rules:
- For ANY card blocking emergency, always put \"Call 16218 IMMEDIATELY\" as the FIRST line
- Cite product_id when referencing specific card policies
- NEVER invent policies not in the retrieved chunks
- For anything outside the knowledge base, say: \"Please call 16218 or visit your nearest Prime Bank branch.\"
- Be concise and action-oriented - cardholders need quick answers
"""


def run(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = [
        f"{banking}_credit_existing_cardholder",
        f"{banking}_credit_i_need_a_credit_card",
    ]
    context = rag_search_multi(search_q, collections, top_k=5)
    history = session.get_history_str()

    prompt = f"""Conversation so far:
{history}

Cardholder's query: {user_message}

Retrieved knowledge base:
{context}

Help the cardholder. If this is an emergency (lost/stolen card), put the helpline first."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.2,
    )

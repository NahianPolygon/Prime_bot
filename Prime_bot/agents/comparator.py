from tools.rag_tool import rag_search_multi
from llm.ollama_client import chat
from memory.session_memory import SessionMemory

SYSTEM = """You are the Prime Bank Credit Card Comparator.
You create side-by-side comparison tables using ONLY the knowledge base chunks provided.

You MUST:
- Use a markdown table for comparisons
- Only include cards explicitly found in the chunks
- Use actual card names in column headers (e.g. "Visa Gold", "Mastercard Platinum")
- Include rows for: Credit Limit, Annual Fee, Fee Waiver, Reward Points, Interest-Free Period, Insurance, Key Benefits, Banking Type
- Leave cell blank or write "N/A" if a value is not in the chunks
- After the table write a 2-3 sentence "Best For" summary per card
- End with: "Would you like to check your eligibility for any of these cards?"

You MUST NOT:
- Invent any card not in the chunks
- Fabricate any number, fee, limit, or benefit
- Guess values not explicitly stated in the chunks
- Display product_id, internal IDs, or system codes like CARD_001 or ISLAMI_CARD_001
- Add extra --- rows between data rows

If the requested cards are not found in chunks, say: "I could not find details for those cards. Please contact Prime Bank at 16218."
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
        "all_products",
    ]
    context = rag_search_multi(search_q, collections, top_k=5, max_context_chars=5000)

    if context.startswith("[NO RESULTS]"):
        return "[NO RESULTS]"

    history = session.get_history_str(max_chars=500)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these for all data):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Create a comparison table using ONLY data found in the chunks above. Use actual card names, never internal codes. Every number in the table must come from the chunks. If a value is not in the chunks, write "N/A".

Provide your comparison now."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.2,
        max_tokens=3000,
        think = True,
    )
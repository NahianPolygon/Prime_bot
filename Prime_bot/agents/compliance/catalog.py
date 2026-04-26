from typing import Generator

from llm.ollama_client import chat, chat_stream
from memory.session_memory import SessionMemory
from tools.rag_tool import list_all_products

CATALOG_SYSTEM = """You are the Prime Bank Product Catalog assistant.

You MUST:
- Use ONLY the product list provided below to answer
- Give exact counts when asked
- Present cards grouped logically based on what the user asked
- Include card name, card network, tier, and banking type for each card
- If asked about a specific category, filter and show only matching cards

You MUST NOT:
- Add any card not in the provided list
- Guess or fabricate any product details
- Display product_id, internal IDs, or system codes to the user
"""


def _build_catalog_summary() -> str | None:
    all_products = list_all_products()
    if not all_products:
        return None

    conventional = [p for p in all_products if p["banking_type"] == "conventional"]
    islami = [p for p in all_products if p["banking_type"] == "islami"]

    lines = []
    for product in all_products:
        parts = [product["product_name"]]
        if product.get("card_network"):
            parts.append(f"Network: {product['card_network']}")
        if product.get("tier"):
            parts.append(f"Tier: {product['tier']}")
        parts.append(f"Banking: {product['banking_type']}")
        lines.append("- " + " | ".join(parts))

    return (
        f"COMPLETE PRODUCT LIST ({len(all_products)} credit cards total):\n"
        f"Conventional: {len(conventional)} cards\n"
        f"Islamic: {len(islami)} cards\n\n"
        + "\n".join(lines)
    )


def _build_prompt(user_message: str, session: SessionMemory, catalog_summary: str) -> str:
    history = session.get_history_str(max_chars=1000)
    return f"""PRODUCT CATALOG (use ONLY this list):
{catalog_summary}

---

Conversation so far:
{history}

User asked: {user_message}

Answer using ONLY the product list above. Show exact counts and card details as requested."""


def run_catalog(
    user_message: str,
    session: SessionMemory,
) -> str:
    catalog_summary = _build_catalog_summary()
    if catalog_summary is None:
        return "[NO RESULTS] No products found in catalog."

    return chat(
        messages=[{"role": "user", "content": _build_prompt(user_message, session, catalog_summary)}],
        system=CATALOG_SYSTEM,
        temperature=0.1,
        max_tokens=1000,
        think=False,
    )


def run_catalog_stream(
    user_message: str,
    session: SessionMemory,
) -> Generator[str, None, None]:
    catalog_summary = _build_catalog_summary()
    if catalog_summary is None:
        yield "[NO RESULTS] No products found in catalog."
        return

    for token in chat_stream(
        messages=[{"role": "user", "content": _build_prompt(user_message, session, catalog_summary)}],
        system=CATALOG_SYSTEM,
        temperature=0.1,
        max_tokens=1000,
        think=False,
    ):
        yield token

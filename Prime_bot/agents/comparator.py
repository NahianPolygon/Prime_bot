from tools.rag_tool import rag_search_multi
from llm.ollama_client import chat
from memory.session_memory import SessionMemory
from logging_utils import log_event
import json
import re


SYSTEM = """You are the Prime Bank Credit Card Comparator.
You extract card comparison data from knowledge base chunks and output ONLY structured JSON.

Output format (JSON only, no markdown, no explanation):
{
  "cards": [
    {
      "name": "Actual Card Name (e.g. Visa Gold, Mastercard Platinum)",
      "credit_limit": "exact value from chunks or N/A",
      "annual_fee": "exact value from chunks or N/A",
      "fee_waiver": "exact condition from chunks or N/A",
      "reward_points": "exact rate from chunks or N/A",
      "interest_free_period": "exact value from chunks or N/A",
      "insurance": "exact coverage from chunks or N/A",
      "key_benefits": "top 3-4 benefits from chunks, comma separated, or N/A",
      "banking_type": "Conventional or Islamic"
    }
  ],
  "best_for": [
    "Card Name: 2-3 sentence summary of ideal user"
  ]
}

Rules:
- ONLY include actual credit cards (e.g. "Visa Gold Credit Card", "Mastercard Platinum Credit Card")
- Do NOT include lounges, services, features, or benefits as separate cards
- "Balaka VIP Lounge", "LoungeKey", "Priority Pass", "BOGO Dining" are BENEFITS of cards, NOT cards themselves
- Include ALL credit cards found in the chunks that match the user request
- Use actual card names, NEVER internal codes like CARD_001 or ISLAMI_CARD_001
- Every value must come directly from the chunks
- Use "N/A" for any value not explicitly stated in the chunks
- Output ONLY valid JSON, nothing else
"""

TABLE_FEATURES = [
    ("Credit Limit", "credit_limit"),
    ("Annual Fee", "annual_fee"),
    ("Fee Waiver", "fee_waiver"),
    ("Reward Points", "reward_points"),
    ("Interest-Free Period", "interest_free_period"),
    ("Insurance", "insurance"),
    ("Key Benefits", "key_benefits"),
    ("Banking Type", "banking_type"),
]

NOT_CARDS = [
    "balaka", "lounge", "loungekey", "priority pass", "bogo",
    "dining", "insurance", "emi", "reward", "airport", "mga",
    "welcome service", "cheque", "fund transfer", "myprime",
]


def _clean_context(context: str) -> str:
    context = re.sub(r'product_id:\s*\S+', '', context)
    context = re.sub(r'\b(?:CARD|ISLAMI_CARD)_\d+\b', '', context)
    context = re.sub(r'$$\s*$$', '', context)
    context = re.sub(r'\n\s*\n\s*\n', '\n\n', context)
    return context.strip()


def _parse_json_response(text: str) -> dict:
    cleaned = re.sub(r'```(?:json)?', '', text).strip()
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        return json.loads(match.group())
    return {}


def _is_valid_card(name: str) -> bool:
    name_lower = name.lower().strip()
    if not name_lower:
        return False
    for pattern in NOT_CARDS:
        if name_lower == pattern or (pattern in name_lower and "card" not in name_lower and "visa" not in name_lower and "mastercard" not in name_lower and "jcb" not in name_lower):
            return False
    return True


def _filter_cards(data: dict) -> dict:
    if "cards" not in data:
        return data
    valid_cards = [c for c in data["cards"] if _is_valid_card(c.get("name", ""))]
    data["cards"] = valid_cards
    if "best_for" in data and valid_cards:
        valid_names = {c["name"].lower() for c in valid_cards}
        filtered_best = []
        for entry in data["best_for"]:
            entry_lower = entry.lower()
            for vn in valid_names:
                if vn in entry_lower:
                    filtered_best.append(entry)
                    break
        data["best_for"] = filtered_best
    return data


def _build_comparison_table(data: dict) -> str:
    cards = data.get("cards", [])
    if not cards:
        return "I could not find details for those cards. Please contact Prime Bank at 16218."

    header = "| Feature |"
    sep = "| --- |"
    for card in cards:
        name = card.get("name", "Unknown")
        header += f" {name} |"
        sep += " --- |"

    rows = [header, sep]
    for label, key in TABLE_FEATURES:
        row = f"| {label} |"
        for card in cards:
            val = card.get(key, "N/A")
            if not val or str(val).strip() == "":
                val = "N/A"
            row += f" {val} |"
        rows.append(row)

    table = "\n".join(rows)

    best_for = data.get("best_for", [])
    if best_for:
        table += "\n\n**Best For:**\n"
        for entry in best_for:
            table += f"\n- **{entry}**"

    table += "\n\nWould you like to check your eligibility for any of these cards?"

    return table


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

    topic_context = rag_search_multi(search_q, collections, top_k=5, max_context_chars=3000)

    if topic_context.startswith("[NO RESULTS]"):
        return "[NO RESULTS]"

    spec_query = "credit limit annual fee reward points interest-free period insurance fee waiver"
    spec_context = rag_search_multi(spec_query, collections, top_k=5, max_context_chars=3000)

    if spec_context.startswith("[NO RESULTS]"):
        context = _clean_context(topic_context)
    else:
        context = _clean_context(topic_context + "\n\n---\n\n" + spec_context)

    history = session.get_history_str(max_chars=500)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these for all data):
{context}

---

Conversation so far:
{history}

User request: {user_message}

Extract comparison data for ALL credit cards found in the chunks that match the user request.
ONLY include actual credit cards (Visa, Mastercard, JCB cards).
Do NOT include lounges, services, or features as separate cards.
Use actual card names, never internal codes.
Every value must come from the chunks. Use "N/A" if not found.
Output ONLY valid JSON."""

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.2,
        max_tokens=3000,
        think=True,
    )

    log_event(
        "comparator_llm_response",
        response_chars=len(response),
        response_preview=response[:300],
    )

    try:
        data = _parse_json_response(response)
        log_event(
            "comparator_json_parsed",
            card_count=len(data.get("cards", [])),
            card_names=[c.get("name", "") for c in data.get("cards", [])],
        )

        data = _filter_cards(data)
        log_event(
            "comparator_cards_filtered",
            card_count=len(data.get("cards", [])),
            card_names=[c.get("name", "") for c in data.get("cards", [])],
        )

        if data and "cards" in data and len(data["cards"]) > 0:
            table = _build_comparison_table(data)
            log_event(
                "comparator_table_built",
                table_chars=len(table),
                table_preview=table[:200],
            )
            return table

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        log_event("comparator_json_error", error=str(e))

    return "I could not find details for those cards. Please contact Prime Bank at 16218."
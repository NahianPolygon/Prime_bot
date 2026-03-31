import json
import re
from tools.rag_tool import rag_search_multi, list_all_products
from llm.ollama_client import chat
from memory.session_memory import SessionMemory


ELIGIBILITY_FIELDS = {
    "age":                 "What is your **age**?",
    "employment_type":     "What is your employment status? (**salaried**, **self-employed**, or **business owner**?)",
    "monthly_income":      "What is your approximate **monthly income** in BDT? (e.g. 50,000 or 1 lakh)",
    "employment_duration": "How long have you been employed / running your business? (e.g. '2 years', '8 months')",
    "has_etin":            "Do you have a valid **E-TIN** (Tax Identification Number)? (yes / no)",
}

ELIGIBILITY_SYSTEM = """You are the Prime Bank Eligibility Advisor.
You assess whether a user qualifies for Prime Bank credit cards.

You MUST:
- Compare the user's profile against eligibility criteria in the chunks
- For EACH card in chunks give: ✅ Likely Eligible | ❌ Likely Ineligible | ⚠️ Borderline
- Cite product_id for every card
- If ineligible for one, suggest alternatives from the chunks

You MUST NOT:
- Invent eligibility criteria not in the chunks
"""

FAQ_SYSTEM = """You are the Prime Bank FAQ & Compliance specialist.

You MUST:
- Answer using ONLY the knowledge base chunks provided
- Cite product_id for any fee or policy
- Use bullet points for document lists and steps

You MUST NOT:
- Invent fees, policies, or requirements not in the chunks

If information is missing say: "Please contact Prime Bank at 16218 for the most current information."
"""

APPLY_SYSTEM = """You are the Prime Bank Application Guide.

You MUST:
- Explain the application process using ONLY the knowledge base chunks provided
- List required documents from the chunks
- Mention any fees or conditions from the chunks
- Cite product_id for any specific card

You MUST NOT:
- Invent any steps, documents, or fees not in the chunks

If information is missing say: "Please contact Prime Bank at 16218 for application details."
"""

CATALOG_SYSTEM = """You are the Prime Bank Product Catalog assistant.

You MUST:
- Use ONLY the product list provided below to answer
- Give exact counts when asked
- Present cards grouped logically based on what the user asked
- Include product_id, card network, tier, and banking type for each card
- If asked about a specific category, filter and show only matching cards

You MUST NOT:
- Add any card not in the provided list
- Guess or fabricate any product details
"""

EXTRACT_SYSTEM = """You extract profile fields from user messages for a bank eligibility check.

RULES:
- Return ONLY a valid JSON object
- Only include keys you can confidently extract
- Valid keys and formats:
  age: integer (e.g. 32)
  employment_type: "salaried" or "self_employed" or "business_owner"
  monthly_income: integer in BDT (convert "1 lakh" to 100000, "50k" to 50000)
  employment_duration: string (e.g. "2 years", "6 months", "16 years")
  has_etin: true or false
- Return {} if nothing can be extracted

EXAMPLES:
User: "32" → currently asking age → {"age": 32}
User: "salaried" → currently asking employment → {"employment_type": "salaried"}
User: "1 lakh per month" → {"monthly_income": 100000}
User: "50000" → currently asking income → {"monthly_income": 50000}
User: "2 years" → {"employment_duration": "2 years"}
User: "yes" → currently asking etin → {"has_etin": true}
User: "no" → currently asking etin → {"has_etin": false}

JSON only. No explanation."""


def _get_collections(banking: str, suffix: str) -> list[str]:
    if banking == "both":
        return [
            f"conventional_credit_{suffix}",
            f"islami_credit_{suffix}",
        ]
    return [f"{banking}_credit_{suffix}"]


def _extract_profile(message: str, session: SessionMemory):
    profile = session.user_profile
    missing = [f for f in ELIGIBILITY_FIELDS if f not in profile or not profile[f]]

    if not missing:
        return

    current_field = missing[0]

    prompt = f"""Currently asking for: {current_field}
Question shown to user: {ELIGIBILITY_FIELDS[current_field]}
User replied: "{message}"

Extract the value for {current_field} from the user's reply. Return JSON."""

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system=EXTRACT_SYSTEM,
        temperature=0.0,
        max_tokens=300,
    )

    try:
        result = re.sub(r'```(?:json)?', '', result).strip()
        match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
        if match:
            extracted = json.loads(match.group())
            for k, v in extracted.items():
                if k in ELIGIBILITY_FIELDS and v is not None and str(v).strip():
                    if k not in session.user_profile or not session.user_profile[k]:
                        session.update_profile(k, v)
    except Exception:
        pass


def _collect_profile(user_message: str, session: SessionMemory) -> tuple[str, bool]:
    _extract_profile(user_message, session)

    missing = [f for f in ELIGIBILITY_FIELDS if f not in session.user_profile or not str(session.user_profile[f]).strip()]

    if missing:
        next_field = missing[0]
        question = ELIGIBILITY_FIELDS[next_field]
        done = len(ELIGIBILITY_FIELDS) - len(missing)
        total = len(ELIGIBILITY_FIELDS)
        response = (
            f"To check your eligibility, I need a few quick details "
            f"({done}/{total} collected so far).\n\n"
            f"{question}"
        )
        return response, False

    return "", True


def run_eligibility(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> tuple[str, bool]:
    response, complete = _collect_profile(user_message, session)

    if not complete:
        return response, False

    banking = routing["banking_type"]
    collections = _get_collections(banking, "i_need_a_credit_card")
    if banking != "both":
        other = "islami" if banking == "conventional" else "conventional"
        collections.append(f"{other}_credit_i_need_a_credit_card")

    context = rag_search_multi(
        "eligibility requirements age income employment duration etin documents",
        collections,
        top_k=8,
    )
    profile_str = session.get_profile_str()

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

User profile:
{profile_str}

The user asked: {user_message}

Assess eligibility for each Prime Bank credit card found in the chunks. Cite product_id."""

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        system=ELIGIBILITY_SYSTEM,
        temperature=0.3,
    )
    return response, True


def run_catalog(
    user_message: str,
    session: SessionMemory,
) -> str:
    all_products = list_all_products()
    history = session.get_history_str(max_chars=1000)

    if not all_products:
        return "[NO RESULTS] No products found in catalog."

    conventional = [p for p in all_products if p["banking_type"] == "conventional"]
    islami = [p for p in all_products if p["banking_type"] == "islami"]

    lines = []
    for p in all_products:
        parts = [f"{p['product_name']} [{p['product_id']}]"]
        if p.get("card_network"):
            parts.append(f"Network: {p['card_network']}")
        if p.get("tier"):
            parts.append(f"Tier: {p['tier']}")
        parts.append(f"Banking: {p['banking_type']}")
        lines.append("- " + " | ".join(parts))

    catalog_summary = f"""COMPLETE PRODUCT LIST ({len(all_products)} credit cards total):
Conventional: {len(conventional)} cards
Islamic: {len(islami)} cards

{chr(10).join(lines)}"""

    prompt = f"""PRODUCT CATALOG (use ONLY this list):
{catalog_summary}

---

Conversation so far:
{history}

User asked: {user_message}

Answer using ONLY the product list above. Show exact counts and card details as requested."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=CATALOG_SYSTEM,
        temperature=0.1,
        max_tokens=1000,
    )


def run_apply(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = _get_collections(banking, "i_need_a_credit_card")
    collections += _get_collections(banking, "existing_cardholder")
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

User question: {user_message}

Explain the application process using ONLY the chunks above. Cite product_id for any specific card."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=APPLY_SYSTEM,
        temperature=0.2,
    )


def run_faq(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = _get_collections(banking, "i_need_a_credit_card")
    collections += _get_collections(banking, "existing_cardholder")
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

User question: {user_message}

Answer using ONLY the chunks above. Cite product_id for any fees or policies."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=FAQ_SYSTEM,
        temperature=0.2,
    )
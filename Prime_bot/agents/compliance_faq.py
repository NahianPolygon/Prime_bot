import json
import re
from tools.rag_tool import rag_search_multi, list_all_products
from llm.ollama_client import chat
from memory.session_memory import SessionMemory
from logging_utils import log_event


def _clean_context(context: str) -> str:
    context = re.sub(r'product_id:\s*\S+', '', context)
    context = re.sub(r'\b(?:CARD|ISLAMI_CARD)_\d+\b', '', context)
    context = re.sub(r'\n\s*\n\s*\n', '\n\n', context)
    return context.strip()


def _safe_int(value, default=0):
    if value is None or str(value).strip() == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


ELIGIBILITY_SCHEMA = {
    "age": {
        "label": "Age",
        "type": "number",
        "placeholder": "e.g. 30",
        "min": 18,
        "max": 70,
        "required": True,
    },
    "employment_type": {
        "label": "Employment Status",
        "type": "select",
        "options": [
            {"value": "salaried", "label": "Salaried"},
            {"value": "self_employed", "label": "Self-Employed"},
            {"value": "business_owner", "label": "Business Owner"},
        ],
        "required": True,
    },
    "monthly_income": {
        "label": "Monthly Income (BDT)",
        "type": "number",
        "placeholder": "e.g. 50000",
        "min": 0,
        "required": True,
    },
    "employment_duration_years": {
        "label": "Employment Duration (Years)",
        "type": "select",
        "options": [{"value": i, "label": str(i)} for i in range(0, 41)],
        "required": True,
    },
    "employment_duration_months": {
        "label": "Employment Duration (Months)",
        "type": "select",
        "options": [{"value": i, "label": str(i)} for i in range(0, 12)],
        "required": False,
    },
    "has_etin": {
        "label": "Do you have a valid E-TIN?",
        "type": "checkbox",
        "required": False,
    },
}

ELIGIBILITY_SYSTEM = """You are the Prime Bank Eligibility Advisor.
You assess whether a user qualifies for Prime Bank credit cards.

You MUST:
- Compare the user's profile against eligibility criteria in the chunks
- Use the pre-computed annual_income from the profile — do NOT calculate it yourself
- For EACH card assessed give: ✅ Likely Eligible | ❌ Likely Ineligible | ⚠️ Borderline
- Always use the actual card name (e.g. "Visa Gold", "Mastercard Platinum") not internal codes
- If ineligible, suggest alternatives from the chunks using their actual card names
- Provide detailed reasoning for each assessment covering: age, income, employment duration, E-TIN
- Your response must be comprehensive and cover all relevant criteria from the chunks
- Conclude with a clear recommendation and the next step (e.g. "You can apply at any Prime Bank branch")

You MUST NOT:
- Invent eligibility criteria not in the chunks
- Calculate or estimate annual income yourself — use only the annual_income provided in the profile
- Display product_id, internal IDs, or system codes like CARD_001 or ISLAMI_CARD_001
- Give extremely brief responses — always explain your reasoning
"""

FAQ_SYSTEM = """You are the Prime Bank FAQ & Compliance specialist.

You MUST:
- Answer using ONLY the knowledge base chunks provided
- Use bullet points for document lists and steps

You MUST NOT:
- Invent fees, policies, or requirements not in the chunks
- Display product_id, internal IDs, or system codes to the user

If information is missing say: "Please contact Prime Bank at 16218 for the most current information."
"""

APPLY_SYSTEM = """You are the Prime Bank Application Guide.

You MUST:
- Explain the application process using ONLY the knowledge base chunks provided
- List required documents from the chunks
- Mention any fees or conditions from the chunks

You MUST NOT:
- Invent any steps, documents, or fees not in the chunks
- Display product_id, internal IDs, or system codes to the user

If information is missing say: "Please contact Prime Bank at 16218 for application details."
"""

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


def _llm_target_card_match(user_message: str, history: str = "") -> str:
    products = list_all_products()
    valid_products = [p for p in products if p.get("product_name")]
    card_names = [p["product_name"] for p in valid_products]

    if not card_names:
        return ""

    card_list = "\n".join(
        f'- {p["product_name"]} | banking_type={p.get("banking_type", "")} | network={p.get("card_network", "")} | tier={p.get("tier", "")}'
        for p in valid_products
    )

    prompt = f"""Available Prime Bank credit cards:
{card_list}

The user said: "{user_message}"

Conversation history:
{history}

Determine whether the user is referring to one specific card from the list above.
Return ONLY the exact card name from the list, or "none" if the message is generic, broad, or does not point to one specific card.

Be robust to:
- partial names like "Hasanah Gold" or "Mastercard World"
- reordered names like "World Mastercard"
- casual references like "the halal gold card"
- exact eligibility/detail/apply questions about a single card

Examples:
- "Am I eligible for Mastercard World Credit Card?" -> "Mastercard World Credit Card"
- "Tell me about Visa Hasanah Gold" -> "Visa Hasanah Gold Credit Card"
- "Can I apply for the halal gold card?" -> "Visa Hasanah Gold Credit Card"
- "What is JCB Gold Credit Card?" -> "JCB Gold Credit Card"
- "does Visa Platinum have lounge access?" -> "Visa Platinum Credit Card"
- "How much is the annual fee for Mastercard Platinum?" -> "Mastercard Platinum Credit Card"
- "show me islami cards" -> "none"
- "check my eligibility" -> "none"
- "which cards does Prime Bank offer?" -> "none"
"""

    response = ""
    for _ in range(2):
        response = chat(
            messages=[{"role": "user", "content": prompt}],
            system="Match the user's message to one specific card from the provided list. Return only the exact card name from the list or 'none'. Never return a paraphrase.",
            temperature=0.0,
            max_tokens=80,
        )
        response = response.strip().strip('"').strip("'")
        if response:
            break

    log_event(
        "llm_full_list_match",
        query=user_message[:80],
        llm_response=response[:80],
    )

    if not response or response.lower() in ("none", "n/a", "unknown", ""):
        return ""

    for name in card_names:
        if response.lower() == name.lower():
            return name

    for name in card_names:
        if response.lower() in name.lower() or name.lower() in response.lower():
            return name

    return ""


def get_eligibility_form_schema(target_card: str = "", profile: dict | None = None) -> dict:
    schema = {
        "target_card": target_card,
        "fields": ELIGIBILITY_SCHEMA,
    }
    if profile:
        prefill = {}
        if profile.get("monthly_income"):
            prefill["monthly_income"] = profile["monthly_income"]
        if profile.get("employment_type"):
            prefill["employment_type"] = profile["employment_type"]
        if profile.get("age"):
            prefill["age"] = profile["age"]
        if prefill:
            schema["prefill"] = prefill
    return schema


def extract_target_card(user_message: str, history: str = "") -> str:
    full_match = _llm_target_card_match(user_message, history)
    if full_match:
        log_event("target_card_resolved", method="llm_full_list", card=full_match)
        return full_match

    log_event("target_card_resolved", method="none", card="")
    return ""


def validate_eligibility_form(form_data: dict) -> list[str]:
    errors = []

    age = form_data.get("age")
    if age is None or str(age).strip() == "":
        errors.append("Age is required.")
    else:
        try:
            age_int = int(age)
            if age_int < 18 or age_int > 70:
                errors.append("Age must be between 18 and 70.")
        except (ValueError, TypeError):
            errors.append("Age must be a valid number.")

    emp = form_data.get("employment_type")
    if not emp or emp not in ("salaried", "self_employed", "business_owner"):
        errors.append("Please select a valid employment status.")

    income = form_data.get("monthly_income")
    if income is None or str(income).strip() == "":
        errors.append("Monthly income is required.")
    else:
        try:
            income_int = int(income)
            if income_int < 0:
                errors.append("Monthly income cannot be negative.")
            elif income_int == 0:
                errors.append("Please enter your actual monthly income.")
        except (ValueError, TypeError):
            errors.append("Monthly income must be a valid number.")

    years = form_data.get("employment_duration_years")
    if years is None or str(years).strip() == "":
        errors.append("Employment duration (years) is required.")
    else:
        try:
            int(years)
        except (ValueError, TypeError):
            errors.append("Employment duration (years) must be a valid number.")

    return errors


def _build_profile_from_form(form_data: dict) -> dict:
    profile = {
        "age": _safe_int(form_data.get("age"), 0),
        "employment_type": form_data.get("employment_type", ""),
        "monthly_income": _safe_int(form_data.get("monthly_income"), 0),
        "has_etin": bool(form_data.get("has_etin", False)),
    }

    years = _safe_int(form_data.get("employment_duration_years"), 0)
    months = _safe_int(form_data.get("employment_duration_months"), 0)
    duration_parts = []
    if years:
        duration_parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months:
        duration_parts.append(f"{months} month{'s' if months != 1 else ''}")
    profile["employment_duration"] = " ".join(duration_parts) if duration_parts else "0 months"

    return profile


def _enrich_profile_str(profile: dict) -> str:
    if not profile:
        return "No user profile information collected yet."

    lines = []
    field_labels = {
        "age": "Age",
        "employment_type": "Employment Type",
        "monthly_income": "Monthly Income (BDT)",
        "employment_duration": "Employment Duration",
        "has_etin": "Has E-TIN",
    }

    for k, label in field_labels.items():
        if k in profile:
            lines.append(f"- {label}: {profile[k]}")

    monthly = profile.get("monthly_income")
    if monthly:
        try:
            monthly_int = int(monthly)
            annual = monthly_int * 12
            annual_lakh = annual / 100_000
            lines.append(f"- annual_income: {annual:,} BDT ({annual_lakh:.1f} lakh)")
        except (ValueError, TypeError):
            pass

    return "Known about user:\n" + "\n".join(lines)


def _get_collections(banking: str, suffix: str) -> list[str]:
    if banking == "both":
        return [
            f"conventional_credit_{suffix}",
            f"islami_credit_{suffix}",
        ]
    return [f"{banking}_credit_{suffix}"]


MIN_ELIGIBILITY_RESPONSE_CHARS = 300
MAX_ELIGIBILITY_RETRIES = 2

_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was too brief. "
    "Provide a COMPLETE assessment covering EVERY criterion: age, income, employment duration, E-TIN, and your final verdict. "
    "Do not stop until you have covered all criteria and given a clear recommendation."
)


def run_eligibility(
    form_data: dict,
    session: SessionMemory,
) -> str:
    profile = _build_profile_from_form(form_data)

    for k, v in profile.items():
        session.update_profile(k, v)

    target = form_data.get("target_card", "")

    collections = [
        "conventional_credit_i_need_a_credit_card",
        "islami_credit_i_need_a_credit_card",
    ]

    eligibility_terms = "eligibility requirements age income employment duration etin documents"
    search_query = f"{target} {eligibility_terms}" if target else eligibility_terms

    context = rag_search_multi(search_query, collections, top_k=8)

    if context.startswith("[NO RESULTS]"):
        return "I couldn't find eligibility criteria in my knowledge base. Please contact Prime Bank at **16218** for eligibility information."

    context = _clean_context(context)
    profile_str = _enrich_profile_str(profile)

    if target:
        focus = (
            f'The user specifically asked about: "{target}"\n'
            "Focus your assessment on that card ONLY. If it is found in the chunks, assess eligibility for that card only. "
            "If not found, say so and suggest the closest alternatives.\n"
            "You MUST provide a detailed assessment including all criteria: age requirement, income requirement, "
            "employment duration, E-TIN requirement, and your verdict."
        )
    else:
        focus = (
            "Assess eligibility for each Prime Bank credit card found in the chunks.\n"
            "For each card provide: the card name, all eligibility criteria checked, and your verdict.\n"
            "Be thorough and detailed."
        )

    base_prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

User profile:
{profile_str}

{focus}

Provide your eligibility assessment now. Use the annual_income value from the profile directly — do not calculate it yourself.
Your response MUST be detailed and comprehensive. Do not cut short."""

    prompt = base_prompt
    response = ""

    for attempt in range(MAX_ELIGIBILITY_RETRIES + 1):
        response = chat(
            messages=[{"role": "user", "content": prompt}],
            system=ELIGIBILITY_SYSTEM,
            temperature=0.2,
            max_tokens=2000,
        )

        if response and len(response.strip()) >= MIN_ELIGIBILITY_RESPONSE_CHARS:
            return response

        if attempt < MAX_ELIGIBILITY_RETRIES:
            prompt = base_prompt + _RETRY_SUFFIX

    if response and len(response.strip()) >= 20:
        return response

    return "I couldn't complete the eligibility assessment. Please contact Prime Bank at **16218** for assistance."


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
        parts = [p["product_name"]]
        if p.get("card_network"):
            parts.append(f"Network: {p['card_network']}")
        if p.get("tier"):
            parts.append(f"Tier: {p['tier']}")
        parts.append(f"Banking: {p['banking_type']}")
        lines.append("- " + " | ".join(parts))

    catalog_summary = (
        f"COMPLETE PRODUCT LIST ({len(all_products)} credit cards total):\n"
        f"Conventional: {len(conventional)} cards\n"
        f"Islamic: {len(islami)} cards\n\n"
        + "\n".join(lines)
    )

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

    context = _clean_context(context)
    history = session.get_history_str(max_chars=1000)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User question: {user_message}

Explain the application process using ONLY the chunks above. Do not display any product_id or internal codes."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=APPLY_SYSTEM,
        temperature=0.2,
        max_tokens=2000,
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

    context = _clean_context(context)
    history = session.get_history_str(max_chars=1000)

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User question: {user_message}

Answer using ONLY the chunks above. Do not display any product_id or internal codes."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=FAQ_SYSTEM,
        temperature=0.2,
    )

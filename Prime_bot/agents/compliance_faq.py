import re
from typing import Generator

from llm.ollama_client import chat, chat_stream
from memory.session_memory import SessionMemory
from logging_utils import log_event
from tools.rag_tool import rag_search, rag_search_multi, list_all_products


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


_NORMALIZE_RE = re.compile(r"[^a-z0-9\s]+")


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("credit card", " ")
    text = text.replace("master card", "mastercard")
    text = text.replace("shariah", "islami")
    text = text.replace("islamic", "islami")
    text = text.replace("hasannah", "hasanah")
    text = text.replace("hasnah", "hasanah")
    text = _NORMALIZE_RE.sub(" ", text)
    return " ".join(text.split())


def _product_aliases(product: dict) -> set[str]:
    name = product.get("product_name", "")
    banking = (product.get("banking_type") or "").lower()
    network = (product.get("card_network") or "").lower()
    tier = (product.get("tier") or "").lower()
    normalized_name = _normalize_text(name)

    aliases = {
        normalized_name,
        normalized_name.replace(" credit card", "").strip(),
    }

    parts = [part for part in (network, "hasanah" if "hasanah" in normalized_name else "", tier) if part]
    if parts:
        aliases.add(" ".join(parts))
        aliases.add(" ".join(parts + ["card"]))

    if network and tier:
        aliases.add(f"{network} {tier}")
        aliases.add(f"{tier} {network}")
        aliases.add(f"{network} {tier} card")

    if banking == "islami" and tier:
        aliases.add(f"islami {tier}")
        aliases.add(f"islami {tier} card")
        aliases.add(f"halal {tier}")
        aliases.add(f"halal {tier} card")
        aliases.add(f"hasanah {tier}")
        aliases.add(f"hasanah {tier} card")

    return {alias.strip() for alias in aliases if alias.strip()}


def _alias_score(message: str, product: dict) -> float:
    msg_tokens = set(message.split())
    best = 0.0
    for alias in _product_aliases(product):
        alias_tokens = set(alias.split())
        if len(alias_tokens) < 2:
            continue
        if alias in message:
            best = max(best, 100.0 + len(alias_tokens))
            continue
        overlap = len(alias_tokens & msg_tokens)
        if overlap:
            ratio = overlap / len(alias_tokens)
            if ratio >= 0.6:
                best = max(best, ratio * 10.0 + overlap)
    return best


def _rag_candidate_bonus(user_message: str, products: list[dict]) -> dict[str, float]:
    by_id = {p.get("product_id", ""): p for p in products}
    bonuses: dict[str, float] = {}
    try:
        items = rag_search(user_message, "all_products", top_k=5)
    except Exception:
        return bonuses

    for rank, item in enumerate(items):
        pid = item.get("product_id", "")
        product = by_id.get(pid)
        if not product:
            continue
        base = max(0.0, 5.0 - rank)
        distance = float(item.get("distance", 1.0))
        bonuses[pid] = max(bonuses.get(pid, 0.0), base + max(0.0, 1.0 - distance))
    return bonuses


def _grounded_target_card_match(user_message: str, history: str = "") -> str:
    products = list_all_products()
    valid_products = [p for p in products if p.get("product_name")]
    if not valid_products:
        return ""

    combined = _normalize_text(f"{history} {user_message}".strip())
    if not combined:
        return ""

    rag_bonus = _rag_candidate_bonus(combined, valid_products)
    scored = []
    for product in valid_products:
        pid = product.get("product_id", "")
        score = _alias_score(combined, product) + rag_bonus.get(pid, 0.0)
        scored.append((product, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    top = [(item[0]["product_name"], round(item[1], 3)) for item in scored[:5]]
    best_product, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0

    log_event(
        "grounded_card_match",
        query=user_message[:80],
        top_5=str(top),
        best_score=round(best_score, 3),
        margin=round(best_score - second_score, 3),
    )

    if best_score >= 100.0:
        return best_product["product_name"]
    if best_score >= 12.0 and (best_score - second_score) >= 1.5:
        return best_product["product_name"]
    return ""


def get_eligibility_form_schema(
    target_card: str = "",
    profile: dict | None = None,
    recommended_cards: list[str] | None = None,
) -> dict:
    schema = {
        "target_card": target_card,
        "fields": ELIGIBILITY_SCHEMA,
    }
    if recommended_cards:
        schema["recommended_cards"] = recommended_cards
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


def _meta_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).split(",")
    return [str(item).strip().lower() for item in items if str(item).strip()]


def extract_recommended_card_names(text: str) -> list[str]:
    if not text:
        return []

    matched = []
    lowered = text.lower()
    products = sorted(
        list_all_products(),
        key=lambda item: len(item.get("product_name", "")),
        reverse=True,
    )
    for product in products:
        name = product.get("product_name", "").strip()
        if name and name.lower() in lowered and name not in matched:
            matched.append(name)
    return matched


def extract_target_card(user_message: str, history: str = "") -> str:
    full_match = _grounded_target_card_match(user_message, history)
    if full_match:
        log_event("target_card_resolved", method="grounded_corpus_match", card=full_match)
        return full_match

    log_event("target_card_resolved", method="none", card="")
    return ""


PREFERENCE_FORM_SCHEMA = {
    "banking_type": {
        "label": "Banking Preference",
        "type": "button_group",
        "options": [
            {"value": "conventional", "label": "Conventional"},
            {"value": "islami", "label": "Islamic (Halal)"},
            {"value": "both", "label": "No Preference"},
        ],
        "required": True,
    },
    "use_case": {
        "label": "Primary Use",
        "type": "tile_grid",
        "options": [
            {"value": "shopping", "label": "Shopping & Daily Use"},
            {"value": "travel", "label": "Travel & Lounge"},
            {"value": "dining", "label": "Dining & Lifestyle"},
            {"value": "rewards_earning", "label": "Rewards & Cashback"},
            {"value": "business_spending", "label": "Business Spending"},
            {"value": "entry_level_premium", "label": "First Premium Card"},
        ],
        "required": True,
    },
    "income_band": {
        "label": "Monthly Income",
        "type": "button_group",
        "options": [
            {"value": "under_50k", "label": "Below BDT 50K"},
            {"value": "50k_100k", "label": "BDT 50K-100K"},
            {"value": "100k_200k", "label": "BDT 100K-200K"},
            {"value": "200k_plus", "label": "BDT 200K+"},
        ],
        "required": True,
    },
    "travel_frequency": {
        "label": "Travel Frequency",
        "type": "button_group",
        "options": [
            {"value": "rare", "label": "Rarely"},
            {"value": "occasional", "label": "Sometimes"},
            {"value": "frequent", "label": "Frequently"},
        ],
        "required": True,
    },
    "tier_preference": {
        "label": "Card Tier Preference",
        "type": "button_group",
        "options": [
            {"value": "gold", "label": "Accessible / Gold"},
            {"value": "premium", "label": "Premium"},
            {"value": "no_preference", "label": "No Preference"},
        ],
        "required": True,
    },
}


def get_preference_form_schema() -> dict:
    return {"fields": PREFERENCE_FORM_SCHEMA}


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
    recommended_cards = session.user_profile.get("recommended_cards", [])
    if not isinstance(recommended_cards, list):
        recommended_cards = []

    collections = [
        "conventional_credit_i_need_a_credit_card",
        "islami_credit_i_need_a_credit_card",
    ]

    eligibility_terms = "eligibility requirements age income employment duration etin documents"
    if target:
        search_query = f"{target} {eligibility_terms}"
    elif recommended_cards:
        search_query = f"{' '.join(recommended_cards)} {eligibility_terms}"
    else:
        search_query = eligibility_terms

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
    elif recommended_cards:
        focus = (
            "The user previously received these recommended cards:\n"
            + "\n".join(f"- {card}" for card in recommended_cards[:3])
            + "\nAssess eligibility for those recommended cards ONLY if they are present in the chunks.\n"
            "For each card provide a separate verdict and reasoning for age, income, employment duration, and E-TIN."
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
            think=False,
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
        think=False,
    )


def run_catalog_stream(
    user_message: str,
    session: SessionMemory,
) -> Generator[str, None, None]:
    all_products = list_all_products()
    history = session.get_history_str(max_chars=1000)

    if not all_products:
        yield "[NO RESULTS] No products found in catalog."
        return

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

    for token in chat_stream(
        messages=[{"role": "user", "content": prompt}],
        system=CATALOG_SYSTEM,
        temperature=0.1,
        max_tokens=1000,
        think=False,
    ):
        yield token


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
        think=False,
    )


def run_apply_stream(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> Generator[str, None, None]:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = _get_collections(banking, "i_need_a_credit_card")
    collections += _get_collections(banking, "existing_cardholder")
    collections.append("all_products")
    collections = list(dict.fromkeys(collections))

    context = rag_search_multi(search_q, collections, top_k=6)
    if context.startswith("[NO RESULTS]"):
        yield "[NO RESULTS]"
        return

    context = _clean_context(context)
    history = session.get_history_str(max_chars=1000)
    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User question: {user_message}

Explain the application process using ONLY the chunks above. Do not display any product_id or internal codes."""

    for token in chat_stream(
        messages=[{"role": "user", "content": prompt}],
        system=APPLY_SYSTEM,
        temperature=0.2,
        max_tokens=2000,
        think=False,
    ):
        yield token


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
        think=False,
    )


def run_faq_stream(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> Generator[str, None, None]:
    banking = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = _get_collections(banking, "i_need_a_credit_card")
    collections += _get_collections(banking, "existing_cardholder")
    collections.append("all_products")
    collections = list(dict.fromkeys(collections))

    context = rag_search_multi(search_q, collections, top_k=6)
    if context.startswith("[NO RESULTS]"):
        yield "[NO RESULTS]"
        return

    context = _clean_context(context)
    history = session.get_history_str(max_chars=1000)
    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Conversation so far:
{history}

User question: {user_message}

Answer using ONLY the chunks above. Do not display any product_id or internal codes."""

    for token in chat_stream(
        messages=[{"role": "user", "content": prompt}],
        system=FAQ_SYSTEM,
        temperature=0.2,
        max_tokens=1800,
        think=False,
    ):
        yield token


RECOMMENDATION_SYSTEM = """You are the Prime Bank Card Recommendation Specialist.

Based on the customer's stated preferences and the knowledge base chunks provided, recommend the 1-2 BEST matching Prime Bank credit cards.

You MUST:
- Recommend at most 2 cards that best match the customer's stated preferences
- Explain clearly WHY each recommended card fits their needs using specific features from the chunks
- Highlight the most relevant benefits for their primary use case
- Conclude with an invitation to check eligibility or visit any Prime Bank branch

You MUST NOT:
- Recommend more than 2 cards
- Invent features, fees, or benefits not in the chunks
- Display product_id, internal IDs, or system codes like CARD_001
"""

_RECOMMENDATION_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Respond now with exactly 1 or 2 card recommendations grounded in the chunks. "
    "For each card include the card name, why it matches the customer, and the strongest specific benefits from the chunks."
)


def run_card_recommendation(form_data: dict, session: SessionMemory) -> str:
    banking_type = form_data.get("banking_type", "both")
    use_case = form_data.get("use_case", "")
    income_band = form_data.get("income_band", "")
    travel_frequency = form_data.get("travel_frequency", "")
    tier_preference = form_data.get("tier_preference", "no_preference")

    products = list_all_products(
        banking_type_filter=banking_type if banking_type in ("conventional", "islami") else None
    )
    if not products:
        return (
            "I couldn't find suitable card recommendations in my knowledge base. "
            "Please contact Prime Bank at **16218** for personalised advice."
        )

    if banking_type in ("conventional", "islami"):
        collections = [f"{banking_type}_credit_i_need_a_credit_card"]
    else:
        collections = [
            "conventional_credit_i_need_a_credit_card",
            "islami_credit_i_need_a_credit_card",
        ]

    def score_product(product: dict) -> float:
        score = 0.0
        tier = (product.get("tier") or "").lower()
        network = (product.get("card_network") or "").lower()
        use_cases = set(_meta_list(product.get("use_cases")))

        if use_case and use_case in use_cases:
            score += 5.0
        if use_case == "travel" and use_cases.intersection({"international_travel", "lounge_access", "business_travel"}):
            score += 3.0
        if use_case == "dining" and use_cases.intersection({"premium_lifestyle", "lifestyle"}):
            score += 2.0
        if use_case == "rewards_earning" and use_cases.intersection({"cashback", "high_spenders"}):
            score += 3.0
        if use_case == "business_spending" and use_cases.intersection({"business_travel", "high_spenders"}):
            score += 3.0
        if use_case == "entry_level_premium":
            if tier == "gold":
                score += 4.0
            elif tier in {"platinum", "world"}:
                score += 1.0

        if tier_preference == "gold":
            score += 3.0 if tier == "gold" else -1.0
        elif tier_preference == "premium":
            score += 3.0 if tier in {"platinum", "world"} else 0.0

        if income_band == "under_50k":
            score += 3.0 if tier == "gold" else -2.0
        elif income_band == "50k_100k":
            score += 3.0 if tier == "gold" else 0.0
        elif income_band == "100k_200k":
            score += 2.5 if tier in {"platinum", "world"} else 1.0
        elif income_band == "200k_plus":
            score += 3.0 if tier in {"world", "platinum"} else 1.0

        if tier in {"platinum", "world"} and income_band in {"under_50k", "50k_100k"}:
            score -= 4.0
        if tier == "gold" and income_band in {"under_50k", "50k_100k"}:
            score += 1.5

        if travel_frequency == "frequent":
            if use_cases.intersection({"travel", "international_travel", "lounge_access", "business_travel"}):
                score += 3.0
            if tier in {"platinum", "world"}:
                score += 1.0
        elif travel_frequency == "rare" and tier == "gold":
            score += 1.0

        if use_case == "rewards_earning" and network == "mastercard" and tier == "world":
            score += 2.0

        return score

    scored_products = sorted(
        products,
        key=lambda product: (score_product(product), product.get("product_name", "")),
        reverse=True,
    )
    shortlisted = [product for product in scored_products[:4] if score_product(product) >= 0]
    if not shortlisted:
        shortlisted = scored_products[:4]
    shortlist_names = [product["product_name"] for product in shortlisted[:4]]

    query_parts = shortlist_names[:]
    if use_case:
        query_parts.append(use_case)
    if travel_frequency == "frequent":
        query_parts.append("lounge travel airport")
    if tier_preference == "gold":
        query_parts.append("gold entry level")
    elif tier_preference == "premium":
        query_parts.append("platinum world premium")
    query_parts.append("credit card features benefits rewards eligibility")
    search_query = " ".join(query_parts)

    context = rag_search_multi(search_query, collections, top_k=5)

    if context.startswith("[NO RESULTS]"):
        return (
            "I couldn't find suitable card recommendations in my knowledge base. "
            "Please contact Prime Bank at **16218** for personalised advice."
        )

    context = _clean_context(context)
    history = session.get_history_str(max_chars=500)

    pref_lines = []
    if banking_type and banking_type != "both":
        label = "Conventional" if banking_type == "conventional" else "Islamic (Shariah-compliant)"
        pref_lines.append(f"- Banking preference: {label}")
    else:
        pref_lines.append("- Banking preference: No preference (show best options)")
    if use_case:
        pref_lines.append(f"- Primary use case: {use_case}")
    if income_band:
        pref_lines.append(f"- Monthly income band: {income_band}")
    if travel_frequency:
        pref_lines.append(f"- Travel frequency: {travel_frequency}")
    if tier_preference:
        pref_lines.append(f"- Tier preference: {tier_preference}")
    if shortlist_names:
        pref_lines.append("- Shortlisted cards from metadata scoring: " + ", ".join(shortlist_names))
    pref_str = "\n".join(pref_lines)

    base_prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

Customer preferences:
{pref_str}

Previous conversation:
{history or 'None'}

Prioritise the shortlisted cards when they are supported by the chunks.
Recommend exactly 1 or 2 cards from the chunks.
For each recommended card, explain specifically why it matches the customer's preferences and mention only benefits that are present in the chunks.
End with a suggestion to check eligibility or visit any Prime Bank branch."""

    prompt = base_prompt
    response = ""
    for attempt in range(2):
        response = chat(
            messages=[{"role": "user", "content": prompt}],
            system=RECOMMENDATION_SYSTEM,
            temperature=0.1,
            max_tokens=1200,
            think=False,
        )
        if response and len(response.strip()) >= 80:
            return response
        prompt = base_prompt + _RECOMMENDATION_RETRY_SUFFIX

    if response and response.strip():
        return response

    return (
        "I couldn't prepare a recommendation just now from my knowledge base. "
        "Please contact Prime Bank at **16218** for personalised advice."
    )

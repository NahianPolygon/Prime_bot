from llm.ollama_client import chat
from memory.session_memory import SessionMemory
from tools.rag_tool import list_all_products, rag_search_multi
from .common import clean_context, meta_list, get_collections

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


def _safe_float(value) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _income_band_monthly_range(income_band: str) -> tuple[float, float | None]:
    if income_band == "under_50k":
        return (0.0, 49_999.0)
    if income_band == "50k_100k":
        return (50_000.0, 99_999.0)
    if income_band == "100k_200k":
        return (100_000.0, 199_999.0)
    if income_band == "200k_plus":
        return (200_000.0, None)
    return (0.0, None)


def run_card_recommendation(form_data: dict, session: SessionMemory) -> str:
    banking_type = form_data.get("banking_type", "both")
    use_case = form_data.get("use_case", "")
    income_band = form_data.get("income_band", "")
    travel_frequency = form_data.get("travel_frequency", "")
    tier_preference = form_data.get("tier_preference", "no_preference")
    known_age = session.user_profile.get("age")
    known_employment = (session.user_profile.get("employment_type") or "").lower()
    known_monthly_income = session.user_profile.get("monthly_income")
    income_floor, income_ceiling = _income_band_monthly_range(income_band)

    products = list_all_products(
        banking_type_filter=banking_type if banking_type in ("conventional", "islami") else None
    )
    if not products:
        return (
            "I couldn't find suitable card recommendations in my knowledge base. "
            "Please contact Prime Bank at **16218** for personalised advice."
        )

    if banking_type in ("conventional", "islami"):
        collections = get_collections(banking_type, "i_need_a_credit_card")
    else:
        collections = get_collections("both", "i_need_a_credit_card")

    def score_product(product: dict) -> float:
        score = 0.0
        tier = (product.get("tier") or "").lower()
        network = (product.get("card_network") or "").lower()
        use_cases = set(meta_list(product.get("use_cases")))
        employment_suitable = set(meta_list(product.get("employment_suitable")))
        feature_category = str(product.get("feature_category") or "").lower()
        age_min = _safe_float(product.get("age_min"))
        age_max = _safe_float(product.get("age_max"))
        income_min = _safe_float(product.get("income_min"))

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

        if feature_category == "existing_cardholder":
            score -= 10.0

        if known_employment and employment_suitable:
            if known_employment in employment_suitable:
                score += 1.5
            else:
                score -= 2.0

        if known_age is not None:
            try:
                age_value = float(known_age)
            except (TypeError, ValueError):
                age_value = None
            if age_value is not None:
                if age_min is not None and age_value < age_min:
                    score -= 8.0
                elif age_max is not None and age_value > age_max:
                    score -= 8.0
                elif age_min is not None or age_max is not None:
                    score += 0.75

        effective_monthly_income = None
        if known_monthly_income not in (None, ""):
            try:
                effective_monthly_income = float(known_monthly_income)
            except (TypeError, ValueError):
                effective_monthly_income = None
        elif income_band:
            effective_monthly_income = income_floor

        if income_min is not None:
            # Frontmatter income_min may represent either monthly or annual thresholds depending on future KB updates.
            # Compare against both monthly and annualized user income and reward whichever interpretation fits.
            if effective_monthly_income is not None:
                annual_income = effective_monthly_income * 12.0
                monthly_gap = effective_monthly_income - income_min
                annual_gap = annual_income - income_min
                if monthly_gap >= 0 or annual_gap >= 0:
                    score += 1.5
                else:
                    score -= 4.0

        if income_band and income_min is not None and income_ceiling is not None and income_min > income_ceiling:
            score -= 3.0

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

    context = clean_context(context)
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
    for _ in range(2):
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

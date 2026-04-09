import json
import re
from tools.rag_tool import rag_search_multi, list_all_products
from llm.ollama_client import chat
from memory.session_memory import SessionMemory


def _clean_context(context: str) -> str:
    context = re.sub(r'product_id:\s*\S+', '', context)
    context = re.sub(r'\b(?:CARD|ISLAMI_CARD)_\d+\b', '', context)
    context = re.sub(r'\n\s*\n\s*\n', '\n\n', context)
    return context.strip()


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
- Use the pre-computed annual_income from the profile — do NOT calculate it yourself
- For EACH card assessed give: ✅ Likely Eligible | ❌ Likely Ineligible | ⚠️ Borderline
- Always use the actual card name (e.g. "Visa Gold", "Mastercard Platinum") not internal codes
- If ineligible, suggest alternatives from the chunks using their actual card names

You MUST NOT:
- Invent eligibility criteria not in the chunks
- Calculate or estimate annual income yourself — use only the annual_income provided in the profile
- Display product_id, internal IDs, or system codes like CARD_001 or ISLAMI_CARD_001
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

EXTRACT_SYSTEM = """You extract profile fields from user messages for a bank eligibility check.

RULES:
- Return ONLY a valid JSON object
- Only include keys you can confidently extract
- Valid keys and formats:
  age: integer (e.g. 32)
  employment_type: "salaried" or "self_employed" or "business_owner"
  monthly_income: integer in BDT (convert "1 lakh" to 100000, "50k" to 50000, "10 lakhs" to 1000000)
  employment_duration: string (e.g. "2 years", "6 months", "16 years", "20 years")
  has_etin: true or false
- Return {} if nothing can be extracted
- Handle natural language: "obviously i have" for etin means true, "nope" means false
- Handle approximate durations: "almost 20 years" means "20 years", "about 3 years" means "3 years"
- Handle typos: "8 tears" means "8 years"
- "business owner", "own business", "entrepreneur" means employment_type is "business_owner"
- "self employed", "freelance", "content creator" means employment_type is "self_employed"
- Any job title like "engineer", "doctor", "teacher" means employment_type is "salaried"

EXAMPLES:
User: "32" -> currently asking age -> {"age": 32}
User: "my age is 66" -> {"age": 66}
User: "salaried" -> currently asking employment -> {"employment_type": "salaried"}
User: "I am a business owner" -> {"employment_type": "business_owner"}
User: "self employed" -> {"employment_type": "self_employed"}
User: "1 lakh per month" -> {"monthly_income": 100000}
User: "i earn 10 lakhs per month" -> {"monthly_income": 1000000}
User: "50000" -> currently asking income -> {"monthly_income": 50000}
User: "2 years" -> {"employment_duration": "2 years"}
User: "for almost 20 years" -> {"employment_duration": "20 years"}
User: "8 tears 3 months" -> {"employment_duration": "8 years 3 months"}
User: "i think for 8 years and 3 months" -> {"employment_duration": "8 years 3 months"}
User: "yes" -> currently asking etin -> {"has_etin": true}
User: "obviously i have" -> currently asking etin -> {"has_etin": true}
User: "nope" -> currently asking etin -> {"has_etin": false}
User: "no" -> currently asking etin -> {"has_etin": false}

JSON only. No explanation."""

BULK_EXTRACT_SYSTEM = """You extract ALL profile fields you can find from the user's message for a bank eligibility check.

RULES:
- Return ONLY a valid JSON object
- Extract ALL fields you can find in the message
- Valid keys and formats:
  age: integer (e.g. 32)
  employment_type: "salaried" or "self_employed" or "business_owner"
  monthly_income: integer in BDT (convert "1 lakh" to 100000, "50k" to 50000, "200k" to 200000, "10 lakhs" to 1000000)
  employment_duration: string (e.g. "2 years", "6 months", "16 years")
  has_etin: true or false
- Return {} if nothing can be extracted
- If user mentions a job title like "software engineer", "doctor", "banker" -> employment_type is "salaried"
- If user mentions "business owner", "own business", "entrepreneur" -> employment_type is "business_owner"
- If user mentions "self employed", "freelance", "content creator" -> employment_type is "self_employed"

EXAMPLES:
User: "I am 33 years old, earn 200k per month and a software engineer and been working for 8 years" -> {"age": 33, "monthly_income": 200000, "employment_type": "salaried", "employment_duration": "8 years"}
User: "25, salaried, 1 lakh income, 3 years experience, have etin" -> {"age": 25, "employment_type": "salaried", "monthly_income": 100000, "employment_duration": "3 years", "has_etin": true}
User: "am i eligible for visa gold?" -> {}
User: "I'm 30 and earn 80k" -> {"age": 30, "monthly_income": 80000}

JSON only. No explanation."""


def _get_collections(banking: str, suffix: str) -> list[str]:
    if banking == "both":
        return [
            f"conventional_credit_{suffix}",
            f"islami_credit_{suffix}",
        ]
    return [f"{banking}_credit_{suffix}"]


def _resolve_target(target: str, history: str) -> str:
    if not target:
        return ""

    prompt = f"""The user asked: "{target}"

Conversation history:
{history}

What specific credit card is the user asking about?
Return ONLY the card name (e.g. "Visa Gold", "Mastercard Platinum", "Visa Hasanah Gold").
If no specific card can be determined, return "none".
Card name only. No explanation."""

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system="Extract the credit card name from context. Return only the card name or 'none'.",
        temperature=0.0,
        max_tokens=50,
    )

    result = result.strip().strip('"').strip("'")
    if result.lower() in ("none", "n/a", "unknown", ""):
        return ""
    return result


def _bulk_extract_profile(message: str, session: SessionMemory):
    prompt = f"""Extract ALL eligibility profile fields from this message:

"{message}"

Return JSON with all fields you can find."""

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system=BULK_EXTRACT_SYSTEM,
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
                    session.update_profile(k, v)
    except Exception:
        pass


def _extract_profile(message: str, session: SessionMemory):
    from logging_utils import log_event

    profile = session.user_profile
    missing = [f for f in ELIGIBILITY_FIELDS if f not in profile or not profile[f]]

    if not missing:
        return

    current_field = missing[0]

    prompt = f"""Currently asking for: {current_field}
Question shown to user: {ELIGIBILITY_FIELDS[current_field]}
User replied: "{message}"

You MUST return a JSON object with the key "{current_field}" and the extracted value.
The user may use informal language, typos, or indirect answers.

Examples for {current_field}:
- If asking employment_duration: "1 year 2 months" -> {{"employment_duration": "1 year 2 months"}}
- If asking employment_duration: "almost one year" -> {{"employment_duration": "1 year"}}
- If asking employment_duration: "for 8 tears" -> {{"employment_duration": "8 years"}}
- If asking employment_type: "self employed" -> {{"employment_type": "self_employed"}}
- If asking employment_type: "i am a content creator" -> {{"employment_type": "self_employed"}}
- If asking has_etin: "obviously i have" -> {{"has_etin": true}}
- If asking age: "my age is 66" -> {{"age": 66}}
- If asking monthly_income: "10 lakhs" -> {{"monthly_income": 1000000}}

Return ONLY valid JSON with the key "{current_field}". Nothing else."""

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system=EXTRACT_SYSTEM,
        temperature=0.0,
        max_tokens=300,
    )

    log_event(
        "extract_profile_debug",
        field=current_field,
        user_message=message,
        llm_raw=result,
    )

    try:
        cleaned = re.sub(r'```(?:json)?', '', result).strip()
        match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
        if match:
            extracted = json.loads(match.group())
            log_event(
                "extract_profile_parsed",
                field=current_field,
                extracted=str(extracted),
            )
            for k, v in extracted.items():
                if k in ELIGIBILITY_FIELDS and v is not None and str(v).strip():
                    if k not in session.user_profile or not session.user_profile[k]:
                        session.update_profile(k, v)
                        log_event("extract_profile_saved", field=k, value=str(v))
                        return
            log_event("extract_profile_no_match", field=current_field, extracted=str(extracted))
        else:
            log_event("extract_profile_no_json", field=current_field, cleaned=cleaned)
    except Exception as e:
        log_event("extract_profile_error", field=current_field, error=str(e))


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


def clear_eligibility_fields(session: SessionMemory):
    for field in ELIGIBILITY_FIELDS:
        if field in session.user_profile:
            session.user_profile[field] = ""


def _enrich_profile_str(session: SessionMemory) -> str:
    profile = session.user_profile
    if not profile:
        return "No user profile information collected yet."

    lines = []
    for k, v in profile.items():
        lines.append(f"- {k}: {v}")

    monthly = profile.get("monthly_income")
    if monthly:
        try:
            monthly_int = int(monthly)
            annual = monthly_int * 12
            annual_lakh = annual / 100000
            lines.append(f"- annual_income: {annual} BDT ({annual_lakh:.1f} lakh)")
        except (ValueError, TypeError):
            pass

    return "Known about user:\n" + "\n".join(lines)


def run_eligibility(
    user_message: str,
    routing: dict,
    session: SessionMemory,
    is_new_check: bool = False,
) -> tuple[str, bool]:
    if is_new_check:
        clear_eligibility_fields(session)
        _bulk_extract_profile(user_message, session)

    response, complete = _collect_profile(user_message, session)

    if not complete:
        return response, False

    banking = routing["banking_type"]
    collections = _get_collections(banking, "i_need_a_credit_card")
    if banking != "both":
        other = "islami" if banking == "conventional" else "conventional"
        collections.append(f"{other}_credit_i_need_a_credit_card")

    target = session.user_profile.get("eligibility_target", "")

    if target:
        resolved = _resolve_target(target, session.get_history_str(max_chars=500))
        if resolved:
            target = resolved
            session.update_profile("eligibility_target", target)

    eligibility_terms = "eligibility requirements age income employment duration etin documents"
    if target:
        search_query = f"{target} {eligibility_terms}"
    else:
        search_query = eligibility_terms

    context = rag_search_multi(
        search_query,
        collections,
        top_k=8,
    )

    if context.startswith("[NO RESULTS]"):
        return "I couldn't find eligibility criteria in my knowledge base. Please contact Prime Bank at **16218** for eligibility information.", True

    context = _clean_context(context)

    profile_str = _enrich_profile_str(session)

    if target:
        focus = f"""The user specifically asked about: "{target}"
Focus your assessment on that card ONLY. If it is found in the chunks, assess eligibility for that card only. If not found, say so and suggest the closest alternatives."""
    else:
        focus = "Assess eligibility for each Prime Bank credit card found in the chunks."

    prompt = f"""KNOWLEDGE BASE CHUNKS (use ONLY these):
{context}

---

User profile:
{profile_str}

{focus}

Provide your eligibility assessment now. Use the annual_income value from the profile directly — do not calculate it yourself."""

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        system=ELIGIBILITY_SYSTEM,
        temperature=0.2,
        max_tokens=1500,
    )

    if not response or len(response.strip()) < 20:
        return "I couldn't complete the eligibility assessment. Please contact Prime Bank at **16218** for assistance.", True

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
        parts = [f"{p['product_name']}"]
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
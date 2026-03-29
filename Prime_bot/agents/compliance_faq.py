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

Rules:
- Compare the user's profile against eligibility criteria in the retrieved knowledge base
- For EACH card found in the chunks, give a clear verdict:
  ✅ Likely Eligible | ❌ Likely Ineligible | ⚠️ Borderline
- Explain the reason based on the specific criteria
- If ineligible for one card, suggest alternatives they might qualify for
- Be honest but encouraging
- Cite product_id for every card you assess
- NEVER invent eligibility criteria not in the retrieved chunks
"""

FAQ_SYSTEM = """You are the Prime Bank FAQ & Compliance specialist.
You answer questions about fees, charges, application process, required documents, and policies.

Rules:
- Cite product_id for any fee or policy you mention
- Use bullet points for document lists and step-by-step processes
- For missing information say: "Please contact Prime Bank at 16218 for the most current information."
- NEVER invent fees, policies, or document requirements not in the retrieved chunks
"""

CATALOG_SYSTEM = """You are the Prime Bank Product Catalog assistant.
You answer questions about how many credit cards Prime Bank offers, what types are available, etc.

Rules:
- Use ONLY the product list provided — do not guess or add unlisted products
- Give exact counts when asked (conventional, Islamic, Visa, Mastercard, Gold, Platinum, etc.)
- Present the full list clearly if asked
- Be factual and precise
"""


def _extract_profile(message: str, session: SessionMemory):
    """
    Rule-based extraction of profile fields from short user answers.
    Handles the common case (yes/no, a number, a word) reliably without
    depending on the LLM returning valid JSON for simple one-word answers.
    Falls back to LLM extraction for complex multi-field messages.
    """
    text    = message.strip().lower()
    profile = session.user_profile

    
    missing       = [f for f in ELIGIBILITY_FIELDS if f not in profile or not profile[f]]
    current_field = missing[0] if missing else None

    if not current_field:
        return  

    extracted = False

    if current_field == "age":
        nums = re.findall(r'\b(\d{1,3})\b', text)
        for n in nums:
            if 16 <= int(n) <= 90:
                session.update_profile("age", int(n))
                extracted = True
                break

    elif current_field == "employment_type":
        if any(w in text for w in ["salaried", "salary", "job", "employee", "employed", "service", "চাকরি"]):
            session.update_profile("employment_type", "salaried")
            extracted = True
        elif any(w in text for w in ["self", "freelance", "freelancer"]):
            session.update_profile("employment_type", "self_employed")
            extracted = True
        elif any(w in text for w in ["business", "owner", "entrepreneur", "ব্যবসা"]):
            session.update_profile("employment_type", "business_owner")
            extracted = True

    elif current_field == "monthly_income":
        clean  = text.replace(",", "")
        lakh_m = re.search(r'(\d+\.?\d*)\s*lakh', clean)
        k_m    = re.search(r'(\d+\.?\d*)\s*k\b', clean)
        plain  = re.search(r'\b(\d{4,7})\b', clean)
        if lakh_m:
            session.update_profile("monthly_income", int(float(lakh_m.group(1)) * 100000))
            extracted = True
        elif k_m:
            session.update_profile("monthly_income", int(float(k_m.group(1)) * 1000))
            extracted = True
        elif plain:
            session.update_profile("monthly_income", int(plain.group(1)))
            extracted = True

    elif current_field == "employment_duration":
        year_m  = re.search(r'(\d+)\s*year', text)
        month_m = re.search(r'(\d+)\s*month', text)
        if year_m or month_m:
            parts = []
            if year_m:  parts.append(f"{year_m.group(1)} year(s)")
            if month_m: parts.append(f"{month_m.group(1)} month(s)")
            session.update_profile("employment_duration", " ".join(parts))
            extracted = True
        elif any(w in text for w in ["just started", "new job", "recently", "less than 1"]):
            session.update_profile("employment_duration", "less than 1 month")
            extracted = True

    elif current_field == "has_etin":
        
        yes_words = ["yes", "have", "got", "i do", "i have", "হ্যাঁ", "আছে", "han", "yeah", "yep", "sure", "correct"]
        no_words  = ["no", "don't", "dont", "do not", "not have", "haven't", "নেই", "না", "nope", "nah"]
        if any(w in text for w in yes_words):
            session.update_profile("has_etin", True)
            extracted = True
        elif any(w in text for w in no_words):
            session.update_profile("has_etin", False)
            extracted = True

    
    if not extracted and len(text.split()) > 4:
        _extract_profile_llm(message, session)


def _extract_profile_llm(message: str, session: SessionMemory):
    """LLM fallback for complex multi-field messages."""
    prompt = f"""Extract personal financial profile information from this message.
Message: "{message}"

Return ONLY a JSON object with any of these keys found (omit keys not mentioned):
- age (integer)
- employment_type (one of: "salaried", "self_employed", "business_owner")
- monthly_income (integer in BDT; convert: "1 lakh"=100000, "50k"=50000)
- employment_duration (string, e.g. "2 years", "6 months")
- has_etin (boolean true or false)

Return {{}} if nothing relevant. Return valid JSON only, no explanation, no markdown."""

    result = chat(messages=[{"role": "user", "content": prompt}], temperature=0.0)

    try:
        
        result = re.sub(r'```(?:json)?', '', result).strip()
        match  = re.search(r'\{[^{}]*\}', result, re.DOTALL)
        if match:
            extracted = json.loads(match.group())
            for k, v in extracted.items():
                if k in ELIGIBILITY_FIELDS and v is not None and str(v).strip():
                    
                    if k not in session.user_profile or not session.user_profile[k]:
                        session.update_profile(k, v)
    except Exception:
        pass


def _collect_profile(user_message: str, session: SessionMemory) -> tuple[str, bool]:
    """
    Conversationally collects eligibility profile fields one at a time.
    Returns (response_text, profile_complete).
    """
    
    _extract_profile(user_message, session)

    
    missing = [f for f in ELIGIBILITY_FIELDS if f not in session.user_profile or not str(session.user_profile[f]).strip()]

    if missing:
        next_field = missing[0]
        question   = ELIGIBILITY_FIELDS[next_field]
        done       = len(ELIGIBILITY_FIELDS) - len(missing)
        total      = len(ELIGIBILITY_FIELDS)
        response   = (
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
    """
    Runs the conversational eligibility flow.
    Returns (response, is_assessment_complete).
    """
    response, complete = _collect_profile(user_message, session)

    if not complete:
        return response, False

    
    banking  = routing["banking_type"]
    collections = [
        f"{banking}_credit_i_need_a_credit_card",
        "conventional_credit_i_need_a_credit_card",
        "islami_credit_i_need_a_credit_card",
    ]
    context     = rag_search_multi(
        "eligibility requirements age income employment duration etin documents",
        collections,
        top_k=8,
    )
    profile_str = session.get_profile_str()

    prompt = f"""User profile:
{profile_str}

Eligibility criteria from knowledge base:
{context}

The user asked: {user_message}

Assess eligibility for each Prime Bank credit card found in the chunks."""

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
    """Answers catalog queries — how many cards, what types, etc."""
    all_products = list_all_products()
    history      = session.get_history_str()

    if all_products:
        conventional = [p for p in all_products if p["banking_type"] == "conventional"]
        islami       = [p for p in all_products if p["banking_type"] == "islami"]
        visa_cards   = [p for p in all_products if "visa" in (p.get("card_network") or p.get("product_name", "")).lower()]
        mc_cards     = [p for p in all_products if "master" in (p.get("card_network") or p.get("product_name", "")).lower()]

        lines = []
        for p in all_products:
            parts = [p["product_name"] or p["product_id"]]
            if p.get("card_network"): parts.append(f"({p['card_network']})")
            if p.get("tier"):         parts.append(f"[{p['tier']}]")
            if p.get("banking_type"): parts.append(f"- {p['banking_type']}")
            lines.append("- " + " ".join(parts))

        catalog_summary = f"""Total credit cards: {len(all_products)}
Conventional banking: {len(conventional)}
Islamic banking: {len(islami)}
Visa network: {len(visa_cards)}
Mastercard network: {len(mc_cards)}

Full product list:
""" + "\n".join(lines)
    else:
        catalog_summary = rag_search_multi(user_message, ["all_products"], top_k=15)

    prompt = f"""Conversation so far:
{history}

User asked: {user_message}

Product catalog:
{catalog_summary}

Answer the user's catalog question accurately using the product list above."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=CATALOG_SYSTEM,
        temperature=0.1,
    )


def run_faq(
    user_message: str,
    routing: dict,
    session: SessionMemory,
) -> str:
    """Answers FAQ, fees, T&C, application process questions."""
    banking  = routing["banking_type"]
    search_q = routing.get("search_query", user_message)

    collections = [
        f"{banking}_credit_i_need_a_credit_card",
        f"{banking}_credit_existing_cardholder",
        "all_products",
    ]
    context = rag_search_multi(search_q, collections, top_k=6)
    history = session.get_history_str()

    prompt = f"""Conversation so far:
{history}

User question: {user_message}

Retrieved knowledge base:
{context}

Answer the FAQ/policy question. Cite product_id for any fees or policies."""

    return chat(
        messages=[{"role": "user", "content": prompt}],
        system=FAQ_SYSTEM,
        temperature=0.2,
    )
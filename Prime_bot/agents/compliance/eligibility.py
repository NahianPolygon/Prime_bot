import re

from llm.ollama_client import chat
from memory.session_memory import SessionMemory
from .common import clean_context, safe_int
from .matching import extract_recommended_card_names
from .schemas import ELIGIBILITY_SCHEMA
from tools.rag_tool import rag_search_multi, rag_search_multi_queries

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

MIN_ELIGIBILITY_RESPONSE_CHARS = 300
MAX_ELIGIBILITY_RETRIES = 2

_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was too brief. "
    "Provide a COMPLETE assessment covering EVERY criterion: age, income, employment duration, E-TIN, and your final verdict. "
    "Do not stop until you have covered all criteria and given a clear recommendation."
)


def get_eligibility_form_schema(
    target_card: str = "",
    profile: dict | None = None,
    recommended_cards: list[str] | None = None,
    scoped_cards: list[str] | None = None,
) -> dict:
    schema = {
        "target_card": target_card,
        "fields": ELIGIBILITY_SCHEMA,
    }
    if recommended_cards:
        schema["recommended_cards"] = recommended_cards
    if scoped_cards:
        schema["scoped_cards"] = scoped_cards
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
        "age": safe_int(form_data.get("age"), 0),
        "employment_type": form_data.get("employment_type", ""),
        "monthly_income": safe_int(form_data.get("monthly_income"), 0),
        "has_etin": bool(form_data.get("has_etin", False)),
    }

    years = safe_int(form_data.get("employment_duration_years"), 0)
    months = safe_int(form_data.get("employment_duration_months"), 0)
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

    for key, label in field_labels.items():
        if key in profile:
            lines.append(f"- {label}: {profile[key]}")

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


def _eligibility_status_from_text(text: str) -> tuple[str, str, str]:
    lowered = (text or "").lower()
    if "❌" in text or "likely ineligible" in lowered or "not eligible" in lowered or "ineligible" in lowered:
        return ("ineligible", "Likely Ineligible", "❌")
    if "⚠️" in text or "borderline" in lowered or "conditional" in lowered:
        return ("borderline", "Borderline", "⚠️")
    if "✅" in text or "likely eligible" in lowered:
        return ("eligible", "Likely Eligible", "✅")
    return ("general", "Needs Review", "ℹ️")


def _clean_reason_line(line: str) -> str:
    text = re.sub(r"^[\-\*\u2022#>\s]+", "", (line or "").strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip(" :.-")


def _reason_lines_from_section(section: str, card_name: str) -> list[str]:
    reasons: list[str] = []
    seen: set[str] = set()
    priority_terms = (
        "age",
        "income",
        "employment",
        "duration",
        "tenure",
        "e-tin",
        "etin",
        "credit",
        "prime bank",
        "relationship",
        "business",
        "salaried",
    )

    for raw_line in section.splitlines():
        line = _clean_reason_line(raw_line)
        if not line:
            continue
        lowered = line.lower()
        if lowered == card_name.lower():
            continue
        if card_name.lower() in lowered and len(line) <= len(card_name) + 10:
            continue
        if not any(term in lowered for term in priority_terms) and not any(sym in raw_line for sym in ("✅", "❌", "⚠️")):
            continue
        if len(line) > 180:
            line = line[:177].rstrip() + "..."
        if line.lower() in seen:
            continue
        seen.add(line.lower())
        reasons.append(line)
        if len(reasons) >= 4:
            break

    return reasons


def extract_eligibility_verdicts(
    text: str,
    target_card: str = "",
    recommended_cards: list[str] | None = None,
    scoped_cards: list[str] | None = None,
) -> list[dict]:
    if not text:
        return []

    recommended_cards = recommended_cards or []
    scoped_cards = scoped_cards or []
    lowered = text.lower()
    discovered_cards = extract_recommended_card_names(text)

    candidates: list[str] = []
    preferred_scope = [target_card, *scoped_cards, *recommended_cards]
    for name in preferred_scope:
        if name and name not in candidates:
            candidates.append(name)

    if not candidates:
        for name in discovered_cards:
            if name and name not in candidates:
                candidates.append(name)

    positions: list[tuple[int, str]] = []
    for name in candidates:
        idx = lowered.find(name.lower())
        if idx >= 0:
            positions.append((idx, name))

    positions.sort(key=lambda item: item[0])
    verdicts: list[dict] = []

    for i, (start, card_name) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        section = text[start:end].strip()
        status, label, badge = _eligibility_status_from_text(section)
        reasons = _reason_lines_from_section(section, card_name)
        if not reasons:
            reasons = _reason_lines_from_section(text, card_name)
        verdicts.append(
            {
                "card_name": card_name,
                "status": status,
                "label": label,
                "badge": badge,
                "reasons": reasons[:3],
            }
        )

    if verdicts:
        return verdicts

    fallback_cards = [name for name in [target_card, *scoped_cards, *recommended_cards] if name]
    if not fallback_cards:
        return []

    status, label, badge = _eligibility_status_from_text(text)
    reasons = _reason_lines_from_section(text, fallback_cards[0])
    return [
        {
            "card_name": card_name,
            "status": status,
            "label": label,
            "badge": badge,
            "reasons": reasons[:3],
        }
        for card_name in fallback_cards
    ]


def build_eligibility_verdict_summary(verdicts: list[dict]) -> str:
    if not verdicts:
        return "Here is a quick summary of the eligibility assessment."

    eligible = [item["card_name"] for item in verdicts if item.get("status") == "eligible"]
    borderline = [item["card_name"] for item in verdicts if item.get("status") == "borderline"]
    ineligible = [item["card_name"] for item in verdicts if item.get("status") == "ineligible"]

    if len(verdicts) == 1:
        item = verdicts[0]
        return f"{item['card_name']}: {item['label']}."

    parts = []
    if eligible:
        parts.append("Strongest match: " + ", ".join(eligible))
    if borderline:
        parts.append("Needs a closer check: " + ", ".join(borderline))
    if ineligible:
        parts.append("Harder fit: " + ", ".join(ineligible))
    return " | ".join(parts) if parts else "Here is a quick summary of the cards checked."


def run_eligibility(
    form_data: dict,
    session: SessionMemory,
) -> str:
    profile = _build_profile_from_form(form_data)

    for key, value in profile.items():
        session.update_profile(key, value)

    target = form_data.get("target_card", "")
    scoped_cards = form_data.get("scoped_cards", [])
    if not isinstance(scoped_cards, list):
        scoped_cards = []
    scoped_cards = [card for card in scoped_cards if isinstance(card, str) and card.strip()]
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
    elif scoped_cards:
        search_query = f"{' '.join(scoped_cards)} {eligibility_terms}"
    elif recommended_cards:
        search_query = f"{' '.join(recommended_cards)} {eligibility_terms}"
    else:
        search_query = eligibility_terms

    context = rag_search_multi_queries(
        [
            search_query,
            f"{search_query} annual income monthly income age etin employment duration",
            f"{search_query} credit limit unsecured collateralized documentation requirements",
        ],
        collections,
        top_k_per_query=4,
        max_context_chars=7600,
    )
    if context.startswith("[NO RESULTS]"):
        context = rag_search_multi(search_query, collections, top_k=8)

    if context.startswith("[NO RESULTS]"):
        return "I couldn't find eligibility criteria in my knowledge base. Please contact Prime Bank at **16218** for eligibility information."

    context = clean_context(context)
    profile_str = _enrich_profile_str(profile)

    if target:
        focus = (
            f'The user specifically asked about: "{target}"\n'
            "Focus your assessment on that card ONLY. If it is found in the chunks, assess eligibility for that card only. "
            "If not found, say so and suggest the closest alternatives.\n"
            "You MUST provide a detailed assessment including all criteria: age requirement, income requirement, "
            "employment duration, E-TIN requirement, and your verdict."
        )
    elif scoped_cards:
        focus = (
            "The user is currently discussing these cards:\n"
            + "\n".join(f"- {card}" for card in scoped_cards)
            + "\nAssess eligibility for these cards ONLY if they are present in the chunks.\n"
            "Do not expand the assessment to other cards unless the user explicitly asked for alternatives.\n"
            "For each card provide a separate verdict and reasoning for age, income, employment duration, and E-TIN."
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

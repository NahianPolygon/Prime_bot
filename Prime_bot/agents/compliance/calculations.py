import math
import re
from datetime import date, timedelta

from kb_config import get_all_products_collection
from memory.session_memory import SessionMemory
from tools.rag_tool import get_product_documents, list_all_products
from .emi import build_emi_calculator_config
from .matching import extract_target_card, resolve_card_candidates


_AMOUNT_RE = re.compile(r"(?:BDT|Tk\.?|৳)?\s*([\d,]{3,})", re.IGNORECASE)
_TENURE_RE = re.compile(r"\b(\d{1,2})\s*[- ]?\s*(?:month|months|mo)\b", re.IGNORECASE)
_POINT_TARGET_RE = re.compile(r"([\d,]{2,})\s*(?:pts|points)\b", re.IGNORECASE)
_MONTH_DAY_RE = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})\b",
    re.IGNORECASE,
)

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def _amount_to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value.replace(",", ""))
    except ValueError:
        return None


def _amounts(text: str) -> list[int]:
    values = [_amount_to_int(match.group(1)) for match in _AMOUNT_RE.finditer(text or "")]
    return [value for value in values if value is not None]


def _main_amount(text: str) -> int | None:
    values = _amounts(text)
    if not values:
        return None
    return max(values)


def _product_by_name() -> dict[str, dict]:
    return {
        product.get("product_name", "").strip().lower(): product
        for product in list_all_products()
        if product.get("product_name")
    }


def _context_cards(session: SessionMemory) -> list[str]:
    cards = session.user_profile.get("active_cards") or session.user_profile.get("recommended_cards") or []
    if not isinstance(cards, list):
        return []
    return [card.strip() for card in cards if isinstance(card, str) and card.strip()]


def _resolve_product(user_message: str, session: SessionMemory, classifier_output: dict) -> dict | None:
    products = _product_by_name()
    names: list[str] = []

    current_target = extract_target_card(user_message, "")
    if current_target:
        names.append(current_target)

    for value in [classifier_output.get("target_card"), *(classifier_output.get("active_cards") or [])]:
        if isinstance(value, str) and value.strip():
            names.append(value.strip())

    if not current_target:
        history_target = extract_target_card(user_message, session.get_history_str(max_chars=800))
        if history_target:
            names.append(history_target)
        names.extend(_context_cards(session))

    if not names:
        names.extend(resolve_card_candidates(user_message, session.get_history_str(max_chars=800), limit=2))

    for name in names:
        product = products.get(name.lower())
        if product:
            return product
    return None


def _product_text(product: dict) -> str:
    docs = get_product_documents(
        product.get("product_name", ""),
        collections=[get_all_products_collection()],
        banking_type_filter=product.get("banking_type") or None,
    )
    return "\n\n".join(doc["text"] for doc in docs)


def _reward_rate(text: str) -> int | None:
    rates = [int(match.group(1)) for match in re.finditer(r"(\d+)\s+points?\s+per\s+BDT\s*50", text or "", re.IGNORECASE)]
    return max(rates) if rates else None


def _interest_free_days(text: str) -> int | None:
    patterns = (
        r"interest[- ]free[^\n]{0,80}?(\d{1,3})\s*days",
        r"fixed at\s+(\d{1,3})\s*days",
        r"(\d{1,3})[- ]day interest[- ]free",
    )
    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _monthly_interest_rate(text: str) -> float | None:
    fallback = None
    for line in (text or "").splitlines():
        lowered = line.lower()
        match = re.search(r"(\d+(?:\.\d+)?)%\s*monthly", line, re.IGNORECASE)
        if not match:
            continue
        value = float(match.group(1))
        if "interest" in lowered and "late payment" not in lowered:
            return value
        if fallback is None and "late payment" not in lowered:
            fallback = value
    return fallback


def _statement_date(text: str) -> date | None:
    match = _MONTH_DAY_RE.search(text or "")
    if not match:
        return None
    month = _MONTHS.get(match.group(1).lower())
    if not month:
        return None
    try:
        return date.today().replace(month=month, day=int(match.group(2)))
    except ValueError:
        return None


def _target_points(text: str) -> int | None:
    values = [_amount_to_int(match.group(1)) for match in _POINT_TARGET_RE.finditer(text or "")]
    values = [value for value in values if value]
    return max(values) if values else None


def _format_bdt(amount: int | float) -> str:
    return f"BDT {math.ceil(amount):,}"


def _format_date(value: date) -> str:
    return f"{value.strftime('%B')} {value.day}"


def _reward_answer(user_message: str, product: dict, text: str) -> tuple[str, dict] | None:
    lowered = user_message.lower()
    if "point" not in lowered and "reward" not in lowered:
        return None
    monthly = _main_amount(user_message)
    rate = _reward_rate(text)
    if not monthly or not rate:
        return None

    points_month = math.floor(monthly / 50) * rate
    points_year = points_month * 12
    target = _target_points(user_message)
    card_name = product.get("product_name", "the card")
    config = {
        "type": "rewards",
        "card_name": card_name,
        "points_per_bdt_50": rate,
        "prefill_monthly_spend": monthly,
        "note": f"{rate} point{'s' if rate != 1 else ''} per BDT 50 on eligible POS/e-commerce spend; excludes cash advances and fees.",
    }

    if target and re.search(r"how many (?:year|years|month|months)|how long|take", lowered):
        months = math.ceil(target / points_month) if points_month else 0
        duration = f"{months} month{'s' if months != 1 else ''}" if months < 12 else f"{months / 12:g} years"
        answer = (
            f"Using **{card_name}** reward earning of **{rate} points per BDT 50**:\n\n"
            f"- Monthly points = ({monthly:,} / 50) x {rate} = **{points_month:,} points**\n"
            f"- Target = **{target:,} points**\n"
            f"- Time needed = {target:,} / {points_month:,} = **{duration}**\n"
        )
        return answer, config

    answer = (
        f"Using **{card_name}** reward earning of **{rate} points per BDT 50**:\n\n"
        f"- Monthly points = ({monthly:,} / 50) x {rate} = **{points_month:,} points**\n"
        f"- Annual points = {points_month:,} x 12 = **{points_year:,} points**\n"
    )
    return answer, config


def _emi_answer(user_message: str, session: SessionMemory, classifier_output: dict, product: dict) -> tuple[str, dict] | None:
    lowered = user_message.lower()
    if "emi" not in lowered and "installment" not in lowered and "instalment" not in lowered:
        return None
    amount = _main_amount(user_message)
    tenure_match = _TENURE_RE.search(user_message)
    tenure = int(tenure_match.group(1)) if tenure_match else None
    if not amount or not tenure:
        return None

    monthly = math.ceil(amount / tenure)
    config = build_emi_calculator_config(user_message, session, classifier_output)
    config["prefill_amount"] = amount
    config["prefill_tenure"] = tenure
    config["selected_card"] = product.get("product_name", config.get("selected_card", ""))
    answer = (
        f"For **{product.get('product_name', 'this card')}**, a **{_format_bdt(amount)}** purchase over **{tenure} months** gives:\n\n"
        f"- Monthly EMI = {amount:,} / {tenure} = **{_format_bdt(monthly)}**\n"
        "- This excludes any one-time conversion/service fee shown in the EMI calculator.\n"
    )
    return answer, config


def _interest_free_answer(user_message: str, product: dict, text: str) -> str | None:
    lowered = user_message.lower()
    if "interest-free" not in lowered and "interest free" not in lowered and "without paying any interest" not in lowered:
        return None
    start = _statement_date(user_message)
    days = _interest_free_days(text)
    if not start or not days:
        return None
    due = start + timedelta(days=days)
    return (
        f"Using **{product.get('product_name', 'this card')}**'s **{days}-day interest-free period**:\n\n"
        f"- Statement date: **{_format_date(start)}**\n"
        f"- Last interest-free date: **{_format_date(due)}**\n"
        "- Pay the full outstanding amount by that date to avoid interest.\n"
    )


def _minimum_payment_answer(user_message: str, product: dict) -> str | None:
    lowered = user_message.lower()
    if "minimum" not in lowered or "pay" not in lowered:
        return None
    amount = _main_amount(user_message)
    if not amount:
        return None
    pct_amount = amount * 0.05
    minimum = max(pct_amount, 5000)
    return (
        f"For **{product.get('product_name', 'this card')}**, the minimum payment rule is **5% of outstanding or BDT 5,000, whichever is higher**.\n\n"
        f"- Outstanding: **{_format_bdt(amount)}**\n"
        f"- 5% of outstanding = **{_format_bdt(pct_amount)}**\n"
        f"- Minimum payable = **{_format_bdt(minimum)}**\n"
    )


def _clean_fact_line(line: str) -> str:
    cleaned = re.sub(r"^[\s>*#`-]+", "", line or "").strip()
    cleaned = re.sub(r"\*\*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    if "|" in cleaned:
        cleaned = " | ".join(part.strip() for part in cleaned.strip("|").split("|") if part.strip())
    return cleaned.strip()


def _fee_waiver_answer(user_message: str, product: dict, text: str) -> str | None:
    lowered = user_message.lower()
    asks_fee = "annual fee" in lowered or "renewal fee" in lowered or "fee waiver" in lowered
    asks_waiver = "waiver" in lowered or "waived" in lowered or "avoid" in lowered or "condition" in lowered
    if not asks_fee or not asks_waiver:
        return None

    candidates: list[str] = []
    for line in (text or "").splitlines():
        line_lower = line.lower()
        mentions_fee = "annual fee" in line_lower or "renewal fee" in line_lower
        mentions_waiver = "waiver" in line_lower or "waived" in line_lower or "do not need to pay" in line_lower
        if mentions_fee and mentions_waiver:
            clean = _clean_fact_line(line)
            if clean:
                candidates.append(clean)

    if not candidates:
        return None

    fact = candidates[0]
    condition_match = re.search(
        r"(\d+)\s*\+?\s*(?:purchases|purchase|transactions|transaction)",
        fact,
        re.IGNORECASE,
    )
    amount_match = re.search(r"BDT\s*([\d,]+)", fact, re.IGNORECASE)
    condition = condition_match.group(0) if condition_match else ""
    amount = f"BDT {amount_match.group(1)}" if amount_match else ""

    lines = [
        f"For **{product.get('product_name', 'this card')}**, I found this fee-waiver term:",
        "",
        f"- **Source term:** {fact}",
    ]
    if condition:
        lines.append(f"- Waiver condition: **{condition}**")
    if amount:
        lines.append(f"- Mentioned fee amount: **{amount}**")
    return "\n".join(lines) + "\n"


def _missed_due_interest_answer(user_message: str, product: dict, text: str) -> str | None:
    lowered = user_message.lower()
    if not ("interest" in lowered and ("miss" in lowered or "late" in lowered or "after one month" in lowered)):
        return None
    amount = _main_amount(user_message)
    rate = _monthly_interest_rate(text)
    if not amount or rate is None:
        return None
    interest = amount * (rate / 100)
    return (
        f"For **{product.get('product_name', 'this card')}**, the available card terms mention **{rate:g}% monthly interest** after the grace period/deadline.\n\n"
        f"- Outstanding balance: **{_format_bdt(amount)}**\n"
        f"- One-month interest = {amount:,} x {rate:g}% = **{_format_bdt(interest)}**\n"
    )


def _bogo_answer(user_message: str, product: dict) -> str | None:
    lowered = user_message.lower()
    if "bogo" not in lowered and "buy one" not in lowered:
        return None
    amounts = _amounts(user_message)
    times_match = re.search(r"\b(\d+)\s*(?:times|x)\s*(?:a|per)?\s*month", user_message, re.IGNORECASE)
    if not amounts or not times_match:
        return None
    meal_cost = amounts[-1]
    times = int(times_match.group(1))
    monthly = meal_cost * times
    annual = monthly * 12
    return (
        f"With **{product.get('product_name', 'this card')}** BOGO dining, assuming one free meal worth **{_format_bdt(meal_cost)}** each visit:\n\n"
        f"- Monthly savings = {meal_cost:,} x {times} = **{_format_bdt(monthly)}**\n"
        f"- Annual savings = {monthly:,} x 12 = **{_format_bdt(annual)}**\n"
    )


def build_deterministic_calculation(
    user_message: str,
    session: SessionMemory,
    classifier_output: dict,
) -> tuple[str, str, dict | None] | None:
    product = _resolve_product(user_message, session, classifier_output)
    if not product:
        return None
    text = _product_text(product)

    emi = _emi_answer(user_message, session, classifier_output, product)
    if emi:
        answer, config = emi
        return answer, "emi", config

    reward = _reward_answer(user_message, product, text)
    if reward:
        answer, config = reward
        return answer, "rewards", config

    for answer in (
        _fee_waiver_answer(user_message, product, text),
        _interest_free_answer(user_message, product, text),
        _minimum_payment_answer(user_message, product),
        _missed_due_interest_answer(user_message, product, text),
        _bogo_answer(user_message, product),
    ):
        if answer:
            return answer, "", None
    return None

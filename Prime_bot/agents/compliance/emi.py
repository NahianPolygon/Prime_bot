import re

from kb_config import get_all_products_collection
from logging_utils import log_event
from memory.session_memory import SessionMemory
from tools.rag_tool import get_product_documents, list_all_products
from .matching import extract_recommended_card_names, extract_target_card, resolve_card_candidates


DEFAULT_EMI_TERMS = {
    "card_name": "",
    "tenures": [12, 24, 36],
    "fee_percent": 1.0,
    "interest_rate_percent": 0.0,
    "min_amount": None,
    "fee_label": "Conversion Fee",
    "note": "0% interest at partner stores; 1% one-time conversion fee applies.",
    "source": "generic_fallback",
}

_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_BDT_RE = re.compile(r"BDT\s*([\d,]+)", re.IGNORECASE)


def _dedupe(items: list[str]) -> list[str]:
    output = []
    seen = set()
    for item in items:
        cleaned = (item or "").strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def _product_by_name() -> dict[str, dict]:
    return {
        product.get("product_name", "").strip().lower(): product
        for product in list_all_products()
        if product.get("product_name")
    }


def _context_card_names(session: SessionMemory) -> list[str]:
    cards = session.user_profile.get("active_cards") or session.user_profile.get("recommended_cards") or []
    if isinstance(cards, list):
        return [card for card in cards if isinstance(card, str) and card.strip()]
    return []


def _resolve_emi_cards(
    user_message: str,
    session: SessionMemory,
    classifier_output: dict,
) -> list[str]:
    names: list[str] = []

    target = (classifier_output.get("target_card") or "").strip()
    if target:
        names.append(target)

    active_cards = classifier_output.get("active_cards") or []
    if isinstance(active_cards, list):
        names.extend(card for card in active_cards if isinstance(card, str))

    names.extend(_context_card_names(session))

    if not names:
        message_target = extract_target_card(user_message, session.get_history_str(max_chars=800))
        if message_target:
            names.append(message_target)

    if not names:
        names.extend(resolve_card_candidates(user_message, session.get_history_str(max_chars=800), limit=3))

    if not names:
        names.extend(extract_recommended_card_names(session.get_last_assistant_response()))

    products = _product_by_name()
    valid_names = []
    for name in _dedupe(names):
        product = products.get(name.lower())
        if product:
            valid_names.append(product["product_name"])

    return _dedupe(valid_names)[:3]


def _emi_text_for_product(product: dict) -> str:
    docs = get_product_documents(
        product.get("product_name", ""),
        collections=[get_all_products_collection()],
        banking_type_filter=product.get("banking_type") or None,
    )
    return "\n\n".join(doc["text"] for doc in docs)


def _parse_tenures(text: str) -> list[int]:
    values: set[int] = set()
    excluded_terms = (
        "salaried",
        "self-employed",
        "self employed",
        "employment",
        "business tenure",
        "months service",
        "bank statement",
        "bank statements",
        "minimum payment",
        "repay over",
    )

    for line in text.splitlines():
        lowered = line.lower()
        if any(term in lowered for term in excluded_terms):
            continue
        has_emi_context = re.search(r"\bemi\b|installment|instalment", lowered) is not None
        has_term_context = "duration" in lowered or "tenure" in lowered
        has_table_context = "purchase" in lowered and "month" in lowered
        if not (has_emi_context or has_term_context or has_table_context):
            continue

        for match in re.finditer(r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})\s*(?:mo|month|months)?\b", line, re.IGNORECASE):
            values.update(int(item) for item in match.groups())

        for match in re.finditer(r"\b(\d{1,2})\s*(?:mo|month|months)\b", line, re.IGNORECASE):
            values.add(int(match.group(1)))

        for match in re.finditer(r"\b(\d{1,2})\s*,\s*(\d{1,2})\s*,?\s*(?:or|and)\s*(\d{1,2})\s*months\b", line, re.IGNORECASE):
            values.update(int(item) for item in match.groups())

    tenures = sorted(value for value in values if 3 <= value <= 60)
    if tenures == [36] and re.search(r"up to\s+36\s+months", text, re.IGNORECASE):
        return [12, 24, 36]
    return tenures or list(DEFAULT_EMI_TERMS["tenures"])


def _parse_fee_percent(text: str) -> float:
    for line in text.splitlines():
        if not re.search(r"emi conversion|conversion fee", line, re.IGNORECASE):
            continue
        match = _PERCENT_RE.search(line)
        if match:
            return float(match.group(1))

    for line in text.splitlines():
        if not re.search(r"service fee", line, re.IGNORECASE):
            continue
        if not re.search(r"\bemi\b|installment|instalment", line, re.IGNORECASE):
            continue
        match = _PERCENT_RE.search(line)
        if match:
            return float(match.group(1))
    return float(DEFAULT_EMI_TERMS["fee_percent"])


def _parse_interest_rate(text: str) -> float:
    for line in text.splitlines():
        lowered = line.lower()
        if "interest" not in lowered and "emi" not in lowered:
            continue
        if not any(term in lowered for term in ("emi", "installment", "instalment", "service charge", "service fee", "ujrah")):
            continue
        match = _PERCENT_RE.search(line)
        if match:
            return float(match.group(1))
    return float(DEFAULT_EMI_TERMS["interest_rate_percent"])


def _parse_min_amount(text: str) -> int | None:
    for line in text.splitlines():
        lowered = line.lower()
        has_purchase_minimum = (
            "purchases over" in lowered
            or "purchase over" in lowered
            or "purchases above" in lowered
            or "purchase above" in lowered
            or "minimum purchase" in lowered
            or "purchase amount minimum" in lowered
        )
        if not has_purchase_minimum:
            continue
        match = _BDT_RE.search(line)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _build_note(terms: dict, is_islami: bool) -> str:
    fee = terms["fee_percent"]
    fee_text = f"{fee:g}%"
    parts = ["0% interest at partner stores"]
    if is_islami:
        parts.append(f"{fee_text} Ujrah-based conversion fee applies")
    else:
        parts.append(f"{fee_text} one-time conversion fee applies")
    if terms.get("min_amount"):
        parts.append(f"minimum purchase BDT {terms['min_amount']:,}")
    return "; ".join(parts) + "."


def _terms_for_product(product: dict) -> dict:
    text = _emi_text_for_product(product)
    is_islami = (product.get("banking_type") or "").lower() == "islami" or "ujrah" in text.lower()

    terms = {
        **DEFAULT_EMI_TERMS,
        "card_name": product.get("product_name", ""),
        "banking_type": product.get("banking_type", ""),
        "tenures": _parse_tenures(text),
        "fee_percent": _parse_fee_percent(text),
        "interest_rate_percent": _parse_interest_rate(text),
        "min_amount": _parse_min_amount(text),
        "fee_label": "Ujrah Conversion Fee" if is_islami else "Conversion Fee",
        "source": "chroma_product_chunks" if text else "generic_fallback",
    }
    terms["note"] = _build_note(terms, is_islami)
    return terms


def build_emi_calculator_config(
    user_message: str,
    session: SessionMemory,
    classifier_output: dict,
) -> dict:
    card_names = _resolve_emi_cards(user_message, session, classifier_output)
    products = _product_by_name()
    cards = []

    for card_name in card_names:
        product = products.get(card_name.lower())
        if not product:
            continue
        cards.append(_terms_for_product(product))

    config = {
        "type": "emi",
        "default": dict(DEFAULT_EMI_TERMS),
        "cards": cards,
    }
    if cards:
        config["selected_card"] = cards[0]["card_name"]

    log_event(
        "emi_calculator_config",
        card_count=len(cards),
        selected_card=config.get("selected_card", ""),
    )
    return config

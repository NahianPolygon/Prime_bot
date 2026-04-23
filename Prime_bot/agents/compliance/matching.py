import re

from logging_utils import log_event
from tools.rag_tool import list_all_products, rag_search

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

    if network and tier and banking != "islami":
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


def _score_products(user_message: str, history: str = "") -> list[tuple[dict, float]]:
    products = list_all_products()
    valid_products = [p for p in products if p.get("product_name")]
    if not valid_products:
        return []

    combined = _normalize_text(f"{history} {user_message}".strip())
    if not combined:
        return []

    rag_bonus = _rag_candidate_bonus(combined, valid_products)
    scored = []
    for product in valid_products:
        pid = product.get("product_id", "")
        score = _alias_score(combined, product) + rag_bonus.get(pid, 0.0)
        scored.append((product, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def _grounded_target_card_match(user_message: str, history: str = "") -> str:
    scored = _score_products(user_message, history)
    if not scored:
        return ""

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


def resolve_card_candidates(user_message: str, history: str = "", limit: int = 3) -> list[str]:
    scored = _score_products(user_message, history)
    if not scored:
        return []

    best_score = scored[0][1]
    if best_score <= 0:
        return []

    cutoff = max(6.0, best_score - 1.5)
    candidates: list[str] = []
    for product, score in scored:
        if len(candidates) >= limit or score < cutoff:
            break
        name = product.get("product_name", "").strip()
        if name and name not in candidates:
            candidates.append(name)
    return candidates


def extract_recommended_card_names(text: str) -> list[str]:
    if not text:
        return []

    matched = []
    normalized_text = _normalize_text(text)
    products = sorted(
        list_all_products(),
        key=lambda item: len(item.get("product_name", "")),
        reverse=True,
    )
    for product in products:
        name = product.get("product_name", "").strip()
        if not name or name in matched:
            continue

        aliases = _product_aliases(product)
        if any(alias in normalized_text for alias in aliases):
            matched.append(name)
    return matched


def extract_target_card(user_message: str, history: str = "") -> str:
    full_match = _grounded_target_card_match(user_message, history)
    if full_match:
        log_event("target_card_resolved", method="grounded_corpus_match", card=full_match)
        return full_match

    log_event("target_card_resolved", method="none", card="")
    return ""

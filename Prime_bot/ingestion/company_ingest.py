from __future__ import annotations

import re
import json
from functools import lru_cache
from pathlib import Path

import chromadb
import yaml
from langchain_text_splitters import MarkdownTextSplitter
from sentence_transformers import SentenceTransformer
from llm.ollama_client import chat as llm_chat


with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)


CHROMA_DIR = _cfg["chroma"]["persist_dir"]
MODEL_NAME = _cfg["embeddings"]["model"]
DOCUMENT_TYPES = frozenset({"i_need_a_credit_card", "existing_cardholder"})
BANKING_TYPES = frozenset({"conventional", "islami", "both"})
COLLECTION_LIMIT = 63
BANKS_ROOT = Path("banks")
_splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=50)

_UNIFIED_MARKDOWN_SYSTEM = """Convert raw bank credit-card content into Prime Bank-style markdown in a single pass.

Return ONLY JSON with exactly these keys:
{
  "archetype": "",
  "product_name": "",
  "card_network": "",
  "tier": "",
  "employment_suitable": [],
  "age_min": null,
  "age_max": null,
  "income_min": null,
  "keywords": [],
  "use_cases": [],
  "body_markdown": ""
}

Allowed archetype values:
- card_product
- documents_required
- dispute_mechanism
- emi_service
- faq_policy
- general_service

Rules:
- Use both the document title and the raw text.
- Treat the requested document type as only a weak hint, not a hard rule.
- Follow Prime Bank markdown architecture closely.
- body_markdown must begin with a single H1 heading using the product name, followed by `##` section headings.
- For card_product, organize around card sections like Overview, What is the card, Eligibility Requirements, Key Features, and any clearly supported benefit sections.
- For documents_required, dispute_mechanism, emi_service, faq_policy, and general_service, organize the body like Prime Bank existing-cardholder/service content with only source-supported sections.
- Do not invent facts. Leave unsupported metadata blank or null.
- Do not write filler such as "not mentioned", "not specified", or "no information available".
- Keep the output concise, factual, and retrieval-friendly.
- Output valid JSON only. Do not include markdown fences.
"""

_ARCHETYPE_ALLOWED = {
    "card_product",
    "documents_required",
    "dispute_mechanism",
    "emi_service",
    "faq_policy",
    "general_service",
}


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_DIR)


def slugify_company_name(company_name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (company_name or "").strip().lower()).strip("_")
    return cleaned or "bank"


def slugify_document_name(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return cleaned or "document"


def safe_meta_value(value):
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _normalize_list(values: list[str] | str | None) -> list[str]:
    if not values:
        return []
    if isinstance(values, str):
        values = [item.strip() for item in values.split(",")]
    normalized = []
    seen = set()
    for value in values:
        item = str(value or "").strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized


def _bounded_collection_name(company_slug: str, suffix: str) -> str:
    raw = f"{company_slug}_{suffix}"
    if len(raw) <= COLLECTION_LIMIT:
        return raw
    overflow = len(raw) - COLLECTION_LIMIT
    trimmed_slug = company_slug[:-overflow].rstrip("_") or company_slug[:8]
    return f"{trimmed_slug}_{suffix}"[:COLLECTION_LIMIT]


def _banking_targets(banking_type: str) -> list[str]:
    if banking_type == "both":
        return ["conventional", "islami"]
    return [banking_type]


def _product_id(bank_slug: str, banking_type: str, document_type: str, file_stem: str) -> str:
    raw = f"{bank_slug}_{banking_type}_{document_type}_{file_stem}"
    return re.sub(r"[^A-Z0-9_]+", "_", raw.upper()).strip("_")


def _markdown_path(bank_slug: str, banking_type: str, document_type: str, file_stem: str) -> Path:
    return BANKS_ROOT / bank_slug / banking_type / "credit" / document_type / f"{file_stem}.md"


def parse_markdown_location(md_file: Path) -> tuple[str, str, str]:
    path = Path(md_file)
    try:
        relative = path.relative_to(BANKS_ROOT)
    except ValueError as exc:
        raise ValueError(f"Markdown file must be under {BANKS_ROOT}/") from exc

    parts = relative.parts
    if len(parts) != 5 or parts[2] != "credit":
        raise ValueError("Markdown path must match banks/<bank>/<banking_type>/credit/<document_type>/<file>.md")

    bank_slug, banking_type, _, document_type, filename = parts
    if not filename.endswith(".md"):
        raise ValueError("Markdown file must end with .md")
    if banking_type not in {"conventional", "islami"}:
        raise ValueError("Markdown banking type must be conventional or islami")
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(f"document_type must be one of: {', '.join(sorted(DOCUMENT_TYPES))}")
    return bank_slug, banking_type, document_type


def _infer_card_network(text: str) -> str:
    lower = (text or "").lower()
    networks = []
    checks = (
        ("Visa", ("visa",)),
        ("Mastercard", ("mastercard", "master card")),
        ("JCB", ("jcb",)),
        ("American Express", ("american express", "amex")),
    )
    for label, needles in checks:
        if any(needle in lower for needle in needles):
            networks.append(label)
    return ", ".join(networks)


_CARD_TIER_LABELS = (
    "world elite",
    "world",
    "signature",
    "infinite",
    "titanium",
    "platinum",
    "gold",
    "classic",
    "standard",
)


def _tier_word_pattern(tier: str) -> str:
    return r"\b" + re.escape(tier).replace(r"\ ", r"\s+") + r"\b"


def _infer_tier_from_title(text: str) -> str:
    lower = (text or "").lower()
    for tier in _CARD_TIER_LABELS:
        if re.search(_tier_word_pattern(tier), lower):
            return tier
    return ""


def _infer_tier_from_body(text: str) -> str:
    lower = (text or "").lower()
    network = r"(?:visa|mastercard|master\s*card|jcb|amex|american\s+express)"
    card_tail = r"(?:credit\s+)?card(?:holder|holders|s)?"

    for tier in _CARD_TIER_LABELS:
        tier_pattern = _tier_word_pattern(tier)
        patterns = (
            rf"{network}[^\n]{{0,80}}{tier_pattern}[^\n]{{0,40}}{card_tail}",
            rf"{tier_pattern}[^\n]{{0,60}}{card_tail}",
        )
        if any(re.search(pattern, lower) for pattern in patterns):
            return tier
    return ""


def _infer_tier(text: str, title_text: str = "") -> str:
    return _infer_tier_from_title(title_text) or _infer_tier_from_body(text)


def _infer_use_cases(text: str) -> list[str]:
    lower = (text or "").lower()
    checks = (
        ("travel", ("travel", "air ticket", "airline", "airport", "international")),
        ("lounge_access", ("lounge", "loungekey", "priority pass", "balaka")),
        ("dining", ("dining", "restaurant", "buffet", "bogo", "buy one get one")),
        ("rewards_earning", ("reward", "rewards", "point", "points", "cashback", "cash back")),
        ("shopping", ("shopping", "retail", "e-commerce", "ecommerce", "pos transaction")),
        ("emi", ("emi", "installment", "instalment", "easy payment")),
        ("balance_transfer", ("balance transfer",)),
        ("premium_lifestyle", ("premium", "privilege", "signature", "platinum", "world")),
    )
    return [label for label, needles in checks if any(needle in lower for needle in needles)]


def _infer_employment_suitable(text: str) -> list[str]:
    lower = (text or "").lower()
    checks = (
        ("salaried", ("salaried", "salary", "employee", "employment")),
        ("business_owner", ("business owner", "businessperson", "self-employed", "self employed", "proprietor")),
        ("professional", ("professional", "doctor", "engineer", "architect", "consultant")),
    )
    return [label for label, needles in checks if any(needle in lower for needle in needles)]


def _heuristic_document_archetype(document_title: str, raw_text: str, document_type: str) -> str:
    haystack = f"{document_title}\n{raw_text}".lower()

    if any(
        needle in haystack
        for needle in (
            "documents required",
            "common requirement",
            "completed application form",
            "valid passport",
            "national id",
            "requirement for salaried",
            "requirement for self employed",
            "photo id",
            "tin",
            "cib form",
        )
    ):
        return "documents_required"

    if any(
        needle in haystack
        for needle in (
            "dispute mechanism",
            "dispute transaction",
            "chargeback",
            "pre-arbitration",
            "arbitration",
            "complaints management",
            "resolution",
            "acquiring bank",
            "60 days",
        )
    ):
        return "dispute_mechanism"

    if any(
        needle in haystack
        for needle in (
            "easycredit",
            "emi plan",
            "installment plan",
            "installment facility",
            "tenure options",
            "reducing balance",
            "processing fee",
            "pre-closure fee",
            "zip facility",
            "want2buy",
            "monthly installment",
        )
    ):
        return "emi_service"

    if any(
        needle in haystack
        for needle in (
            "terms and conditions",
            "schedule of charges",
            "faq",
            "frequently asked questions",
            "policy",
            "conditions apply",
        )
    ):
        return "faq_policy"

    if any(
        needle in haystack
        for needle in (
            "credit card",
            "complimentary access",
            "interest free period",
            "free supplementary card",
            "renewal fee",
            "annual fee",
            "credit limit",
            "reward",
            "lounge",
            "skycoins",
            "travel",
        )
    ) and document_type == "i_need_a_credit_card":
        return "card_product"

    return "general_service" if document_type == "existing_cardholder" else "card_product"


def _service_document_type_for_archetype(archetype: str) -> str:
    if archetype == "card_product":
        return "i_need_a_credit_card"
    return "existing_cardholder"


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text or "").strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def _sanitize_markdown_body(body: str, title: str) -> str:
    cleaned = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", (body or "").strip(), flags=re.MULTILINE).strip()
    if cleaned.startswith("---"):
        parts = cleaned.split("---", 2)
        cleaned = parts[2].strip() if len(parts) >= 3 else cleaned
    lines = [line for line in cleaned.splitlines() if not re.search(r"\b(?:not specified|not mentioned)\b", line, re.IGNORECASE)]
    normalized_lines = []
    heading_names = {
        "overview",
        "what is",
        "what is the service",
        "eligibility requirements",
        "eligibility",
        "key features",
        "lounge access",
        "installment facility",
        "payment options",
        "reward program",
        "contact center",
        "documents required",
        "applicant categories",
        "salaried requirements",
        "self-employed requirements",
        "fees and charges",
        "how to request",
        "how to report",
        "limits and tenure",
        "early settlement",
        "investigation process",
        "resolution timeline",
        "escalation",
        "dispute mechanism",
        "faq",
        "terms and conditions",
    }
    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if stripped and not stripped.startswith("#"):
            if lowered in heading_names or any(lowered.startswith(f"{name} ") for name in heading_names):
                line = f"## {stripped}"
        normalized_lines.append(line)
    lines = normalized_lines
    cleaned = "\n".join(lines).strip()
    if not cleaned.startswith("# "):
        cleaned = re.sub(r"^#+\s*", "", cleaned, count=1).strip()
        cleaned = f"# {title}\n\n{cleaned}" if cleaned else f"# {title}"

    final_lines = cleaned.splitlines()
    heading_names = {
        "overview",
        "what is",
        "what is the service",
        "eligibility requirements",
        "eligibility",
        "key features",
        "lounge access",
        "installment facility",
        "payment options",
        "reward program",
        "contact center",
        "documents required",
        "applicant categories",
        "salaried requirements",
        "self-employed requirements",
        "fees and charges",
        "how to request",
        "how to report",
        "limits and tenure",
        "early settlement",
        "investigation process",
        "resolution timeline",
        "escalation",
        "dispute mechanism",
        "faq",
        "terms and conditions",
    }
    kept: list[str] = []
    i = 0
    while i < len(final_lines):
        line = final_lines[i]
        if line.startswith("## "):
            j = i + 1
            section_lines = []
            while j < len(final_lines) and not final_lines[j].startswith("## "):
                section_lines.append(final_lines[j])
                j += 1
            has_content = any(item.strip() for item in section_lines)
            if has_content:
                kept.append(line)
                kept.extend(section_lines)
            i = j
            continue
        kept.append(line)
        i += 1
    normalized_kept = []
    for index, line in enumerate(kept):
        stripped = line.strip()
        lowered = re.sub(r"^#+\s*", "", stripped).lower()
        if index > 0 and stripped and (lowered in heading_names or any(lowered.startswith(f"{name} ") for name in heading_names)):
            clean_heading = re.sub(r"^#+\s*", "", stripped)
            normalized_kept.append(f"## {clean_heading}")
        else:
            normalized_kept.append(line)
    if len(normalized_kept) > 2 and normalized_kept[0].strip() == f"# {title}":
        second = normalized_kept[1].strip()
        third = normalized_kept[2].strip()
        if not second and third == title:
            del normalized_kept[2]
    return "\n".join(normalized_kept).strip()


def _as_optional_number(value):
    if value in (None, "", "None", "null"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _format_frontmatter_value(value) -> str:
    if value is None:
        return "None"
    if isinstance(value, list):
        return "[" + ", ".join(json.dumps(str(item), ensure_ascii=False) for item in value) + "]"
    if isinstance(value, str):
        if not value:
            return '""'
        if re.fullmatch(r"[A-Za-z0-9_ /&()+.-]+", value):
            return value
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _dump_frontmatter(frontmatter: dict) -> str:
    return "\n".join(f"{key}: {_format_frontmatter_value(value)}" for key, value in frontmatter.items())


def _build_card_frontmatter(
    *,
    bank_slug: str,
    banking_type: str,
    document_title: str,
    product_name: str,
    card_network: str,
    tier: str,
    use_cases: list[str] | None,
    employment_suitable: list[str] | None,
    age_min=None,
    age_max=None,
    income_min=None,
    keywords: list[str] | None = None,
) -> dict:
    product = product_name.strip() or document_title
    return {
        "product_id": _product_id(bank_slug, banking_type, "i_need_a_credit_card", slugify_document_name(product)),
        "product_name": product,
        "banking_type": banking_type,
        "category": "credit_card",
        "card_network": card_network.strip() or "",
        "tier": tier.strip() or "",
        "employment_suitable": _normalize_list(employment_suitable),
        "age_min": age_min,
        "age_max": age_max,
        "income_min": income_min,
        "keywords": _normalize_list(keywords),
        "use_cases": _normalize_list(use_cases),
    }


def _build_service_frontmatter(
    *,
    bank_slug: str,
    banking_type: str,
    document_title: str,
    product_name: str,
    use_cases: list[str] | None,
) -> dict:
    product = product_name.strip() or document_title
    return {
        "product_id": _product_id(bank_slug, banking_type, "existing_cardholder", slugify_document_name(product)),
        "product_name": product,
        "banking_type": banking_type,
        "feature_category": "existing_cardholder",
        "tier": "any",
        "category": "credit_card",
        "use_cases": _normalize_list(use_cases),
    }


def _compose_markdown(frontmatter: dict, body_markdown: str) -> str:
    yaml_text = _dump_frontmatter(frontmatter).strip()
    return f"---\n{yaml_text}\n---\n{body_markdown.strip()}\n"


def _fallback_card_body(title: str, raw_text: str) -> str:
    return (
        f"# {title}\n\n"
        "## Overview\n\n"
        f"{raw_text.strip()}\n"
    ).strip()


def _fallback_service_body(title: str, raw_text: str) -> str:
    return (
        f"# {title}\n\n"
        "## Overview\n\n"
        f"{raw_text.strip()}\n"
    ).strip()


def _normalize_document_with_llm(
    *,
    company_name: str,
    document_title: str,
    raw_text: str,
    banking_type: str,
    requested_document_type: str,
    product_name: str,
    card_network: str,
    tier: str,
    use_cases: list[str],
    employment_suitable: list[str],
) -> tuple[str, dict, str]:
    prompt = (
        f"Bank: {company_name}\n"
        f"Banking type: {banking_type}\n"
        f"Requested document type hint: {requested_document_type}\n"
        f"Document title: {document_title}\n"
        f"Product name hint: {product_name or document_title}\n"
        f"Card network hint: {card_network}\n"
        f"Tier hint: {tier}\n"
        f"Use case hints: {json.dumps(use_cases)}\n"
        f"Employment hints: {json.dumps(employment_suitable)}\n\n"
        "Classify the content based on what the document is actually about, then generate the markdown body.\n\n"
        f"Raw text:\n{raw_text}"
    )
    parsed = _parse_json(
        llm_chat(
            messages=[{"role": "user", "content": prompt}],
            system=_UNIFIED_MARKDOWN_SYSTEM,
            temperature=0.0,
            max_tokens=2400,
            think=False,
        )
    )
    archetype = str(parsed.get("archetype") or "").strip()
    if archetype not in _ARCHETYPE_ALLOWED:
        archetype = _heuristic_document_archetype(document_title, raw_text, requested_document_type)
    title = str(parsed.get("product_name") or product_name or document_title).strip() or document_title
    normalized = {
        "product_name": title,
        "card_network": str(parsed.get("card_network") or card_network or "").strip(),
        "tier": str(parsed.get("tier") or tier or "").strip(),
        "employment_suitable": _normalize_list(parsed.get("employment_suitable")) or employment_suitable,
        "age_min": _as_optional_number(parsed.get("age_min")),
        "age_max": _as_optional_number(parsed.get("age_max")),
        "income_min": _as_optional_number(parsed.get("income_min")),
        "keywords": _normalize_list(parsed.get("keywords")),
        "use_cases": _normalize_list(parsed.get("use_cases")) or use_cases,
    }
    body = _sanitize_markdown_body(parsed.get("body_markdown", ""), title)
    if body == f"# {title}":
        fallback = _fallback_card_body if archetype == "card_product" else _fallback_service_body
        body = fallback(title, raw_text)
    return archetype, normalized, body


def _load_md(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return meta, body
    return {}, text


def _delete_existing_source(collection, source: str) -> None:
    try:
        collection.delete(where={"source": source})
    except Exception:
        pass


def _ingest_markdown_file(
    md_file: Path,
    *,
    bank_slug: str,
    banking_type: str,
    document_type: str,
    replace_existing: bool,
    client: chromadb.PersistentClient,
    embedder: SentenceTransformer,
) -> dict:
    meta, body = _load_md(md_file)
    chunks = [chunk.strip() for chunk in _splitter.split_text(body) if chunk.strip()]
    if not chunks:
        raise ValueError(f"No ingestible text chunks were produced from {md_file}")

    embeddings = embedder.encode(chunks).tolist()
    collections = [
        _bounded_collection_name(bank_slug, "all_products"),
        _bounded_collection_name(bank_slug, f"{banking_type}_credit_{document_type}"),
    ]

    base_meta = {key: safe_meta_value(value) for key, value in meta.items()}
    base_meta["source"] = str(md_file)
    base_meta["collection"] = ""

    doc_key = str(base_meta.get("product_id") or f"{bank_slug}_{banking_type}_{document_type}_{md_file.stem}")
    ids = [f"{doc_key.lower()}_{idx}" for idx in range(len(chunks))]
    inserted = []

    for collection_name in collections:
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        if replace_existing:
            _delete_existing_source(collection, str(md_file))

        collection.upsert(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{**base_meta, "collection": collection_name} for _ in chunks],
            ids=ids,
        )
        inserted.append(collection_name)

    return {
        "document_key": doc_key,
        "markdown_path": str(md_file),
        "collections": inserted,
        "chunk_count": len(chunks),
    }


def ingest_company_text(
    *,
    company_name: str,
    document_title: str,
    raw_text: str,
    document_type: str,
    banking_type: str,
    product_name: str = "",
    card_network: str = "",
    tier: str = "",
    source: str = "",
    use_cases: list[str] | None = None,
    employment_suitable: list[str] | None = None,
    replace_existing: bool = True,
    client: chromadb.PersistentClient | None = None,
    embedder: SentenceTransformer | None = None,
) -> dict:
    company_name = (company_name or "").strip()
    document_title = (document_title or "").strip()
    raw_text = (raw_text or "").strip()
    document_type = (document_type or "").strip()
    banking_type = (banking_type or "").strip()

    if not company_name:
        raise ValueError("company_name is required")
    if not document_title:
        raise ValueError("document_title is required")
    if not raw_text:
        raise ValueError("raw_text is required")
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(f"document_type must be one of: {', '.join(sorted(DOCUMENT_TYPES))}")
    if banking_type not in BANKING_TYPES:
        raise ValueError(f"banking_type must be one of: {', '.join(sorted(BANKING_TYPES))}")

    company_slug = slugify_company_name(company_name)
    file_stem = slugify_document_name(product_name or document_title)
    client = client or get_client()
    embedder = embedder or get_embedder()
    infer_text = " ".join([document_title, product_name, raw_text])
    inferred_card_network = card_network.strip() or _infer_card_network(infer_text)
    title_text = " ".join([document_title, product_name])
    inferred_tier = tier.strip() or _infer_tier(infer_text, title_text)
    inferred_use_cases = _normalize_list(use_cases) or _infer_use_cases(infer_text)
    inferred_employment_suitable = _normalize_list(employment_suitable) or _infer_employment_suitable(infer_text)
    document_archetype, normalized_frontmatter, body_markdown = _normalize_document_with_llm(
        company_name=company_name,
        document_title=document_title,
        raw_text=raw_text,
        banking_type=banking_type,
        requested_document_type=document_type,
        product_name=product_name,
        card_network=inferred_card_network,
        tier=inferred_tier,
        use_cases=inferred_use_cases,
        employment_suitable=inferred_employment_suitable,
    )
    effective_document_type = _service_document_type_for_archetype(document_archetype)

    written_files = []
    for target_banking_type in _banking_targets(banking_type):
        md_path = _markdown_path(company_slug, target_banking_type, effective_document_type, file_stem)
        if md_path.exists() and not replace_existing:
            raise ValueError(f"Markdown file already exists: {md_path}")
        if effective_document_type == "existing_cardholder":
            frontmatter = _build_service_frontmatter(
                bank_slug=company_slug,
                banking_type=target_banking_type,
                document_title=document_title,
                product_name=str(normalized_frontmatter.get("product_name") or product_name or document_title),
                use_cases=normalized_frontmatter.get("use_cases") or inferred_use_cases,
            )
        else:
            frontmatter = _build_card_frontmatter(
                bank_slug=company_slug,
                banking_type=target_banking_type,
                document_title=document_title,
                product_name=str(normalized_frontmatter.get("product_name") or product_name or document_title),
                card_network=str(normalized_frontmatter.get("card_network") or inferred_card_network),
                tier=str(normalized_frontmatter.get("tier") or inferred_tier),
                use_cases=normalized_frontmatter.get("use_cases") or inferred_use_cases,
                employment_suitable=normalized_frontmatter.get("employment_suitable") or inferred_employment_suitable,
                age_min=normalized_frontmatter.get("age_min"),
                age_max=normalized_frontmatter.get("age_max"),
                income_min=normalized_frontmatter.get("income_min"),
                keywords=normalized_frontmatter.get("keywords") or [],
            )
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_compose_markdown(frontmatter, body_markdown), encoding="utf-8")
        written_files.append(md_path)

    documents = []
    collections = []
    chunk_count = 0
    for md_path in written_files:
        meta, _ = _load_md(md_path)
        target_banking_type = str(meta.get("banking_type") or "")
        result = _ingest_markdown_file(
            md_path,
            bank_slug=company_slug,
            banking_type=target_banking_type,
            document_type=effective_document_type,
            replace_existing=replace_existing,
            client=client,
            embedder=embedder,
        )
        documents.append(result)
        chunk_count += int(result["chunk_count"])
        for collection_name in result["collections"]:
            if collection_name not in collections:
                collections.append(collection_name)

    document_keys = [item["document_key"] for item in documents]

    return {
        "company_name": company_name,
        "company_slug": company_slug,
        "bank_name": company_name,
        "bank_slug": company_slug,
        "document_title": document_title,
        "document_type": effective_document_type,
        "requested_document_type": document_type,
        "document_archetype": document_archetype,
        "banking_type": banking_type,
        "collections": collections,
        "chunk_count": chunk_count,
        "document_key": document_keys[0] if len(document_keys) == 1 else ", ".join(document_keys),
        "document_keys": document_keys,
        "markdown_paths": [item["markdown_path"] for item in documents],
        "documents": documents,
    }


def ingest_markdown_path(
    md_file: str | Path,
    *,
    replace_existing: bool = True,
    client: chromadb.PersistentClient | None = None,
    embedder: SentenceTransformer | None = None,
) -> dict:
    path = Path(md_file)
    if not path.exists():
        raise ValueError(f"Markdown file does not exist: {path}")
    bank_slug, banking_type, document_type = parse_markdown_location(path)
    return _ingest_markdown_file(
        path,
        bank_slug=bank_slug,
        banking_type=banking_type,
        document_type=document_type,
        replace_existing=replace_existing,
        client=client or get_client(),
        embedder=embedder or get_embedder(),
    )

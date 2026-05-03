from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import chromadb
import yaml
from langchain_text_splitters import MarkdownTextSplitter
from sentence_transformers import SentenceTransformer


with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)


CHROMA_DIR = _cfg["chroma"]["persist_dir"]
MODEL_NAME = _cfg["embeddings"]["model"]
DOCUMENT_TYPES = frozenset({"i_need_a_credit_card", "existing_cardholder"})
BANKING_TYPES = frozenset({"conventional", "islami", "both"})
COLLECTION_LIMIT = 63
BANKS_ROOT = Path("banks")
_splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=50)


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


def _normalize_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
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


def _build_frontmatter(
    *,
    bank_name: str,
    bank_slug: str,
    banking_type: str,
    document_type: str,
    document_title: str,
    product_name: str,
    card_network: str,
    tier: str,
    source: str,
    use_cases: list[str] | None,
    employment_suitable: list[str] | None,
    file_stem: str,
) -> dict:
    product = product_name.strip() or document_title
    return {
        "product_id": _product_id(bank_slug, banking_type, document_type, file_stem),
        "product_name": product,
        "bank_name": bank_name,
        "bank_slug": bank_slug,
        "banking_type": banking_type,
        "category": "credit_card",
        "document_type": document_type,
        "card_network": card_network.strip() or "",
        "tier": tier.strip() or "",
        "employment_suitable": _normalize_list(employment_suitable),
        "age_min": None,
        "age_max": None,
        "income_min": None,
        "keywords": [],
        "use_cases": _normalize_list(use_cases),
        "source_label": source.strip() or "",
    }


def _compose_markdown(frontmatter: dict, document_title: str, raw_text: str) -> str:
    body = (raw_text or "").strip()
    title = (document_title or frontmatter.get("product_name") or "Document").strip()
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    if not body.startswith("#"):
        body = f"# {title}\n\n{body}"
    return f"---\n{yaml_text}\n---\n{body}\n"


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

    written_files = []
    for target_banking_type in _banking_targets(banking_type):
        md_path = _markdown_path(company_slug, target_banking_type, document_type, file_stem)
        if md_path.exists() and not replace_existing:
            raise ValueError(f"Markdown file already exists: {md_path}")

        frontmatter = _build_frontmatter(
            bank_name=company_name,
            bank_slug=company_slug,
            banking_type=target_banking_type,
            document_type=document_type,
            document_title=document_title,
            product_name=product_name,
            card_network=inferred_card_network,
            tier=inferred_tier,
            source=source,
            use_cases=inferred_use_cases,
            employment_suitable=inferred_employment_suitable,
            file_stem=file_stem,
        )
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_compose_markdown(frontmatter, document_title, raw_text), encoding="utf-8")
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
            document_type=document_type,
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
        "document_type": document_type,
        "banking_type": banking_type,
        "collections": collections,
        "chunk_count": chunk_count,
        "document_key": document_keys[0] if len(document_keys) == 1 else ", ".join(document_keys),
        "document_keys": document_keys,
        "markdown_paths": [item["markdown_path"] for item in documents],
        "documents": documents,
    }

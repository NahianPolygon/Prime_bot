from __future__ import annotations

import hashlib
import re
from functools import lru_cache

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
_splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=50)


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_DIR)


def slugify_company_name(company_name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (company_name or "").strip().lower()).strip("_")
    return cleaned or "company"


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


def build_company_collections(company_name: str, banking_type: str, document_type: str) -> list[str]:
    company_slug = slugify_company_name(company_name)
    if banking_type not in BANKING_TYPES:
        raise ValueError(f"Unsupported banking_type: {banking_type}")
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(f"Unsupported document_type: {document_type}")

    collections = [_bounded_collection_name(company_slug, "all_products")]
    if banking_type == "both":
        collections.extend(
            [
                _bounded_collection_name(company_slug, f"conventional_credit_{document_type}"),
                _bounded_collection_name(company_slug, f"islami_credit_{document_type}"),
            ]
        )
    else:
        collections.append(_bounded_collection_name(company_slug, f"{banking_type}_credit_{document_type}"))
    return collections


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

    client = client or get_client()
    embedder = embedder or get_embedder()

    chunks = [chunk.strip() for chunk in _splitter.split_text(raw_text) if chunk.strip()]
    if not chunks:
        raise ValueError("No ingestible text chunks were produced from raw_text")

    embeddings = embedder.encode(chunks).tolist()
    company_slug = slugify_company_name(company_name)
    collections = build_company_collections(company_name, banking_type, document_type)
    digest = hashlib.sha1(f"{company_slug}|{document_type}|{banking_type}|{document_title}|{raw_text}".encode("utf-8")).hexdigest()[:12]
    doc_key = f"{company_slug}_{document_type}_{digest}"

    meta = {
        "company_name": company_name,
        "company_slug": company_slug,
        "product_name": product_name.strip() or document_title,
        "product_id": doc_key,
        "banking_type": banking_type,
        "category": "credit_card",
        "document_type": document_type,
        "card_network": card_network.strip(),
        "tier": tier.strip(),
        "source": source.strip() or f"uploaded:{document_title}",
        "use_cases": _normalize_list(use_cases),
        "employment_suitable": _normalize_list(employment_suitable),
    }
    base_meta = {key: safe_meta_value(value) for key, value in meta.items()}

    inserted = []
    ids = [f"{doc_key}_{idx}" for idx in range(len(chunks))]

    for collection_name in collections:
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        if replace_existing:
            try:
                collection.delete(ids=ids)
            except Exception:
                pass
        collection.upsert(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{**base_meta, "collection": collection_name} for _ in chunks],
            ids=ids,
        )
        inserted.append(collection_name)

    return {
        "company_name": company_name,
        "company_slug": company_slug,
        "document_title": document_title,
        "document_type": document_type,
        "banking_type": banking_type,
        "collections": inserted,
        "chunk_count": len(chunks),
        "document_key": doc_key,
    }

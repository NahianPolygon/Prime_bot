import re
import yaml
import chromadb
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel, Field
from typing import Optional
from crewai.tools import BaseTool
from kb_config import get_all_products_collection
from logging_utils import log_event

try:
    from rank_bm25 import BM25Okapi as _BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25Okapi = None  # type: ignore
    _BM25_AVAILABLE = False

_RRF_K = 60  # RRF constant — higher values reduce the impact of top-ranked docs

_TOKEN_RE = re.compile(r'\b\w+\b')

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_model = SentenceTransformer(cfg["embeddings"]["model"])
_client = chromadb.PersistentClient(path=cfg["chroma"]["persist_dir"])

_SERVICE_PATTERNS = {"_services_", "cardholder_services", "conv_services", "islami_services"}


class RAGInput(BaseModel):
    query: str = Field(..., description="The user's question to search for")
    collection: str = Field(..., description="ChromaDB collection name to search in")
    top_k: int = Field(default=5, description="Number of chunks to retrieve")
    banking_type_filter: Optional[str] = Field(
        default=None,
        description="Optional filter: 'conventional' or 'islami'",
    )


def _is_service_doc(meta: dict) -> bool:
    pid = (meta.get("product_id") or "").lower()
    pname = (meta.get("product_name") or "").lower()
    for pattern in _SERVICE_PATTERNS:
        if pattern in pid or pattern in pname:
            return True
    if "cardholder" in pname and "service" in pname:
        return True
    return False


def _hybrid_rerank(
    query: str,
    items: list[dict],
    top_k: int,
) -> list[dict]:
    """Re-rank items using BM25 + semantic RRF fusion when rank_bm25 is available."""
    if not _BM25_AVAILABLE or len(items) <= top_k:
        return items[:top_k]

    query_tokens = _TOKEN_RE.findall(query.lower())
    corpus_tokens = [_TOKEN_RE.findall(item["text"].lower()) for item in items]

    try:
        bm25 = _BM25Okapi(corpus_tokens)
        bm25_scores = bm25.get_scores(query_tokens)
    except Exception:
        return items[:top_k]

    # Semantic ranking is already by ascending distance (lower = better)
    semantic_ranks = {i: rank for rank, i in enumerate(range(len(items)))}
    # BM25 ranking: higher score = better rank
    bm25_ranks = {i: rank for rank, i in enumerate(
        sorted(range(len(items)), key=lambda i: bm25_scores[i], reverse=True)
    )}

    rrf_scores = [
        (i, 1.0 / (_RRF_K + semantic_ranks[i]) + 1.0 / (_RRF_K + bm25_ranks[i]))
        for i in range(len(items))
    ]
    rrf_scores.sort(key=lambda x: x[1], reverse=True)

    return [items[i] for i, _ in rrf_scores[:top_k]]


def rag_search(
    query: str,
    collection: str,
    top_k: int = 5,
    banking_type_filter: Optional[str] = None,
) -> list[dict]:
    count_before = 0
    try:
        col = _client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )
        count_before = col.count()
    except Exception as e:
        log_event("rag_error", collection=collection, stage="open_collection", error=str(e))
        return []

    embedding = _model.encode(query).tolist()

    where_filter = None
    if banking_type_filter:
        where_filter = {"banking_type": banking_type_filter}

    # Fetch a wider pool for BM25 re-ranking; fall back to top_k if BM25 unavailable
    fetch_k = (top_k * 3) if _BM25_AVAILABLE else top_k
    try:
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": min(fetch_k, max(col.count(), 1)),
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = col.query(**kwargs)
    except Exception as e:
        log_event("rag_error", collection=collection, stage="query", error=str(e))
        return []

    if not results["documents"] or not results["documents"][0]:
        log_event(
            "rag_query",
            collection=collection,
            top_k=top_k,
            corpus_count=count_before,
            returned=0,
            hybrid=_BM25_AVAILABLE,
        )
        return []

    chunks = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results.get("distances", [[]])[0]

    items = []
    for i, (chunk, meta) in enumerate(zip(chunks, metas)):
        product_id = meta.get("product_id", "")
        product_name = meta.get("product_name", "")
        banking_type = meta.get("banking_type", "")
        source_label = product_name or product_id or meta.get("source", "unknown")
        header = f"[{source_label}]"
        if banking_type:
            header += f" ({banking_type})"
        dist = distances[i] if i < len(distances) else 1.0
        items.append({
            "text": f"{header}\n{chunk}",
            "distance": dist,
            "product_id": product_id,
            "collection": collection,
        })

    items = _hybrid_rerank(query, items, top_k)

    log_event(
        "rag_query",
        collection=collection,
        top_k=top_k,
        corpus_count=count_before,
        returned=len(items),
        hybrid=_BM25_AVAILABLE,
    )

    return items


def _deduplicate(items: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in items:
        text_key = item["text"][:200]
        if text_key not in seen:
            seen.add(text_key)
            deduped.append(item)
    return deduped


def rag_search_multi(
    query: str,
    collections: list[str],
    top_k: int = 5,
    banking_type_filter: Optional[str] = None,
    max_context_chars: int = 6000,
) -> str:
    all_items = []
    hit_collections = 0

    for col_name in collections:
        items = rag_search(query, col_name, top_k, banking_type_filter)
        if items:
            hit_collections += 1
            all_items.extend(items)

    log_event(
        "rag_multi",
        requested_collections=len(collections),
        hit_collections=hit_collections,
        top_k=top_k,
        total_chunks=len(all_items),
    )

    if not all_items:
        return "[NO RESULTS] No relevant information found across all collections."

    all_items = _deduplicate(all_items)
    all_items.sort(key=lambda x: x["distance"])

    output = []
    char_count = 0
    for item in all_items:
        entry = item["text"]
        if char_count + len(entry) > max_context_chars:
            break
        output.append(entry)
        char_count += len(entry)

    if not output:
        output.append(all_items[0]["text"])

    return "\n\n---\n\n".join(output)


def rag_search_multi_queries(
    queries: list[str],
    collections: list[str],
    top_k_per_query: int = 4,
    banking_type_filter: Optional[str] = None,
    max_context_chars: int = 7000,
) -> str:
    cleaned_queries = []
    seen_queries = set()
    for query in queries:
        q = (query or "").strip()
        if not q:
            continue
        key = q.lower()
        if key in seen_queries:
            continue
        seen_queries.add(key)
        cleaned_queries.append(q)

    if not cleaned_queries:
        return "[NO RESULTS] No relevant information found across all collections."

    all_items = []
    hit_collections = 0

    for query_rank, query in enumerate(cleaned_queries):
        for col_name in collections:
            items = rag_search(query, col_name, top_k_per_query, banking_type_filter)
            if items:
                hit_collections += 1
                for item in items:
                    enriched = dict(item)
                    enriched["_query_rank"] = query_rank
                    all_items.append(enriched)

    log_event(
        "rag_multi_queries",
        queries=len(cleaned_queries),
        requested_collections=len(collections),
        hit_collections=hit_collections,
        top_k_per_query=top_k_per_query,
        total_chunks=len(all_items),
    )

    if not all_items:
        return "[NO RESULTS] No relevant information found across all collections."

    all_items = _deduplicate(all_items)
    all_items.sort(key=lambda x: (x.get("distance", 1.0), x.get("_query_rank", 999)))

    output = []
    char_count = 0
    for item in all_items:
        entry = item["text"]
        if char_count + len(entry) > max_context_chars:
            break
        output.append(entry)
        char_count += len(entry)

    if not output:
        output.append(all_items[0]["text"])

    return "\n\n---\n\n".join(output)


def rag_search_single(
    query: str,
    collection: str,
    top_k: int = 5,
    banking_type_filter: Optional[str] = None,
) -> str:
    items = rag_search(query, collection, top_k, banking_type_filter)
    if not items:
        return "[NO RESULTS] No relevant information found in the knowledge base."
    return "\n\n---\n\n".join(item["text"] for item in items)


class RAGTool(BaseTool):
    name: str = "knowledge_base_search"
    description: str = (
        "Search the Prime Bank knowledge base. "
        "Pass the user's question as query and the relevant collection name. "
        "Returns the most relevant document chunks with their source product IDs."
    )
    args_schema: type[BaseModel] = RAGInput

    def _run(
        self,
        query: str,
        collection: str,
        top_k: int = 5,
        banking_type_filter: Optional[str] = None,
    ) -> str:
        return rag_search_single(
            query=query,
            collection=collection,
            top_k=top_k,
            banking_type_filter=banking_type_filter,
        )


def list_all_products(
    banking_type_filter: Optional[str] = None,
    exclude_services: bool = True,
) -> list[dict]:
    try:
        col = _client.get_collection(get_all_products_collection())
    except Exception:
        return []

    try:
        kwargs = {"include": ["metadatas"]}
        if banking_type_filter:
            kwargs["where"] = {"banking_type": banking_type_filter}

        results = col.get(**kwargs)
    except Exception:
        return []

    seen_ids = set()
    products = []
    for meta in results.get("metadatas", []):
        pid = meta.get("product_id") or meta.get("product_name")
        cat = meta.get("category", "")
        if not pid or pid in seen_ids or cat != "credit_card":
            continue
        if exclude_services and _is_service_doc(meta):
            continue
        seen_ids.add(pid)
        network = meta.get("card_network", "")
        product_name = meta.get("product_name", "")
        if not network and "visa" in product_name.lower():
            network = "Visa"
        elif not network and "mastercard" in product_name.lower():
            network = "Mastercard"
        elif not network and "jcb" in product_name.lower():
            network = "JCB"
        products.append(
            {
                "product_id": meta.get("product_id", ""),
                "product_name": product_name,
                "banking_type": meta.get("banking_type", ""),
                "card_network": network,
                "tier": meta.get("tier", ""),
                "category": cat,
                "feature_category": meta.get("feature_category", ""),
                "use_cases": meta.get("use_cases", ""),
                "employment_suitable": meta.get("employment_suitable", ""),
                "age_min": meta.get("age_min", ""),
                "age_max": meta.get("age_max", ""),
                "income_min": meta.get("income_min", ""),
                "keywords": meta.get("keywords", ""),
            }
        )
    return products


def get_product_documents(
    product_name: str,
    collections: Optional[list[str]] = None,
    banking_type_filter: Optional[str] = None,
) -> list[dict]:
    product_name = (product_name or "").strip()
    if not product_name:
        return []

    collection_names = collections or [get_all_products_collection()]
    documents: list[dict] = []
    seen = set()

    for collection_name in collection_names:
        try:
            col = _client.get_collection(collection_name)
        except Exception:
            continue

        try:
            results = col.get(
                where={"product_name": product_name},
                include=["documents", "metadatas"],
            )
        except Exception as e:
            log_event("rag_error", collection=collection_name, stage="get_product_documents", error=str(e))
            continue

        for doc_id, document, meta in zip(
            results.get("ids", []),
            results.get("documents", []),
            results.get("metadatas", []),
        ):
            if banking_type_filter and meta.get("banking_type") != banking_type_filter:
                continue

            key = (collection_name, doc_id)
            if key in seen:
                continue
            seen.add(key)
            documents.append(
                {
                    "id": doc_id,
                    "text": document or "",
                    "metadata": meta or {},
                    "collection": collection_name,
                }
            )

    return documents

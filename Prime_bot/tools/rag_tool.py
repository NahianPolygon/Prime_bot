import yaml
import chromadb
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel, Field
from typing import Optional
from crewai.tools import BaseTool
from logging_utils import log_event

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_model = SentenceTransformer(cfg["embeddings"]["model"])
_client = chromadb.PersistentClient(path=cfg["chroma"]["persist_dir"])


class RAGInput(BaseModel):
    query: str = Field(..., description="The user's question to search for")
    collection: str = Field(..., description="ChromaDB collection name to search in")
    top_k: int = Field(default=5, description="Number of chunks to retrieve")
    banking_type_filter: Optional[str] = Field(
        default=None,
        description="Optional filter: 'conventional' or 'islami'",
    )


def rag_search(
    query: str,
    collection: str,
    top_k: int = 5,
    banking_type_filter: Optional[str] = None,
) -> str:
    count_before = 0
    try:
        col = _client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )
        count_before = col.count()
    except Exception as e:
        log_event("rag_error", collection=collection, stage="open_collection", error=str(e))
        return f"[RAG ERROR] Could not access collection '{collection}': {e}"

    embedding = _model.encode(query).tolist()

    where_filter = None
    if banking_type_filter:
        where_filter = {"banking_type": banking_type_filter}

    try:
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": min(top_k, max(col.count(), 1)),
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = col.query(**kwargs)
    except Exception as e:
        log_event("rag_error", collection=collection, stage="query", error=str(e))
        return f"[RAG ERROR] Query failed on collection '{collection}': {e}"

    if not results["documents"] or not results["documents"][0]:
        log_event(
            "rag_query",
            collection=collection,
            top_k=top_k,
            corpus_count=count_before,
            returned=0,
        )
        return "[NO RESULTS] No relevant information found in the knowledge base."

    chunks = results["documents"][0]
    metas = results["metadatas"][0]
    log_event(
        "rag_query",
        collection=collection,
        top_k=top_k,
        corpus_count=count_before,
        returned=len(chunks),
    )

    output = []
    for chunk, meta in zip(chunks, metas):
        product_id = meta.get("product_id", "")
        product_name = meta.get("product_name", "")
        banking_type = meta.get("banking_type", "")
        source_label = product_id or product_name or meta.get("source", "unknown")
        header = f"[{source_label}]"
        if banking_type:
            header += f" ({banking_type})"
        output.append(f"{header}\n{chunk}")

    return "\n\n---\n\n".join(output)


def rag_search_multi(
    query: str,
    collections: list[str],
    top_k: int = 5,
    banking_type_filter: Optional[str] = None,
) -> str:
    all_results = []
    hit_collections = 0
    for col_name in collections:
        result = rag_search(query, col_name, top_k, banking_type_filter)
        if not result.startswith("[NO RESULTS]") and not result.startswith("[RAG ERROR]"):
            hit_collections += 1
            all_results.append(f"=== From {col_name} ===\n{result}")
    log_event(
        "rag_multi",
        requested_collections=len(collections),
        hit_collections=hit_collections,
        top_k=top_k,
    )
    if not all_results:
        return "[NO RESULTS] No relevant information found across all collections."
    return "\n\n".join(all_results)


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
        return rag_search(
            query=query,
            collection=collection,
            top_k=top_k,
            banking_type_filter=banking_type_filter,
        )


def list_all_products(banking_type_filter: Optional[str] = None) -> list[dict]:
    try:
        col = _client.get_collection("all_products")
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
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            products.append(
                {
                    "product_id": meta.get("product_id", ""),
                    "product_name": meta.get("product_name", ""),
                    "banking_type": meta.get("banking_type", ""),
                    "card_network": meta.get("card_network", ""),
                    "tier": meta.get("tier", ""),
                    "category": meta.get("category", ""),
                }
            )
    return products

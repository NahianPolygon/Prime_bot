# RAG Implementation Architecture - Prime Bank Bot

## Overview

This document details the Retrieval-Augmented Generation (RAG) implementation for the Prime Bank Bot system. The RAG layer enables semantic search across product documentation to provide enhanced context and information retrieval capabilities.

## Architecture Components

### 1. Vector Database: Qdrant
- **Service**: Qdrant vector database (runs in Docker as `prime_bot_qdrant`)
- **Port**: 6333 (gRPC), 6334 (HTTP)
- **Collection**: `prime_products` - stores embeddings of all product documentation
- **Distance Metric**: Cosine similarity for semantic matching
- **Advantages**: High performance, native async support, persistent storage

### 2. Embedding Model: Google Embedding-Gemma-300m
- **Model**: `google/embedding-gemma-300m` (configured in `app/core/config.py`)
- **Dimension**: 300-dimensional vectors
- **Framework**: Sentence-Transformers
- **Characteristics**: Lightweight, efficient, handles financial terminology well

### 3. Knowledge Base Structure

```
app/knowledge/
├── products/
│   ├── conventional/
│   │   ├── credit/
│   │   │   └── i_need_a_credit_card/
│   │   │       ├── visa_gold_credit_card.md
│   │   │       ├── mastercard_platinum_credit_card.md
│   │   │       └── ...
│   │   └── save/
│   │       ├── deposit_accounts/
│   │       └── deposit_schemes/
│   └── islami/
│       └── [similar structure]
└── structured/
    └── [JSON files for fast filtering]
```

### 4. Core RAG Services

#### RAGRetriever (`app/services/rag_retriever.py`)
Singleton service managing vector embeddings and semantic search.

**Key Methods:**
- `__init__()`: Initializes embedder, Qdrant client, creates collection
- `_ensure_collection()`: Verifies Qdrant collection exists, creates if needed
- `_load_documents()`: Chunks MD files and indexes them as vectors
- `_chunk_content()`: Splits text with overlap (500 chars, 100 char overlap)
- `retrieve(query, top_k=3)`: Semantic search returning top K similar chunks

**Flow:**
1. Connect to Qdrant server
2. Load embedder (google/embedding-gemma-300m)
3. Scan all MD files in products directory
4. Chunk content (with sliding window)
5. Encode chunks as vectors
6. Store in Qdrant with metadata (banking_type, product_type, file path)
7. On queries: encode query → search Qdrant → return ranked results

#### RAGEnricher (`app/services/rag_enricher.py`)
Wraps RAGRetriever for higher-level enrichment operations.

**Key Methods:**
- `enrich_product_response(product_name, query)`: Retrieve context for a product
- `answer_product_question(product_name, query)`: Generate LLM answer from RAG context

#### ProductMatcher Integration
Updated `format_products_response()` to:
1. Retrieve products based on structured filters (JSON)
2. For each query, retrieve top RAG results if available
3. Include semantic context in response generation

### 5. Configuration

**app/core/config.py additions:**
```python
EMBEDDING_MODEL: str = "google/embedding-gemma-300m"
QDRANT_HOST: str = "localhost"  (Docker: "qdrant")
QDRANT_PORT: int = 6333
```

**Docker Environment Variables:**
```yaml
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

## Data Flow

### Indexing (On Container Startup)
```
1. RAGRetriever.get_instance() called
2. Connect to Qdrant at qdrant:6333
3. Create "prime_products" collection if not exists
4. Check collection point count:
   - If > 0: Skip (already indexed)
   - If = 0: Index all MD files
5. For each MD file:
   - Read content
   - Chunk text (500 chars, 100 char overlap)
   - Encode chunks with embedder
   - Create PointStruct with embedding + metadata
   - Upsert to Qdrant
```

### Query Processing
```
User Query (e.g., "Show me Islamic cards with lounge access")
    ↓
ClassifyInquiry → Determine query type (PRODUCT_INFO_QUERY)
    ↓
ProductMatcher → Structured filtering (banking_type, employment, etc.)
    ↓
RAG Enhancement (Optional):
  - Encode user query
  - Search Qdrant: query_vector → top 3 results
  - Extract context chunks
  - Return with similarity scores
    ↓
Format Response:
  - Matched products + RAG context
  - Ranked by relevance
    ↓
Return to User
```

## Key Design Decisions

### 1. Hybrid Approach (JSON + RAG)
- **JSON Filtering**: Fast, deterministic, handles strict criteria (age, income, employment)
- **RAG**: Semantic enrichment, handles feature comparisons, flexible queries
- **Synergy**: Filter first (fast) → Enrich with RAG (context)

### 2. Chunking Strategy
- **Size**: 500 characters per chunk
- **Overlap**: 100 characters (10-20% overlap)
- **Reason**: Balances context preservation with vector search efficiency

### 3. Metadata in Payloads
Each vector includes:
```python
{
    'file': 'visa_gold_credit_card.md',
    'banking_type': 'conventional',
    'product_type': 'credit_card',
    'path': '/app/app/knowledge/products/...',
    'chunk': 'First 500 chars of chunk'
}
```
Enables filtering searches by banking_type/product_type post-retrieval.

### 4. Singleton Pattern
- RAGRetriever is singleton to share one Qdrant connection
- Initialized once on first access
- Reused across all requests

### 5. Graceful Degradation
- If Qdrant unavailable: System continues, RAG features disabled
- If embedder unavailable: System continues, no semantic search
- Logged warnings for debugging

## Dependencies

**New packages added to requirements.txt:**
- `sentence-transformers==5.1.0` - Embedding models
- `transformers==4.55.2` - HuggingFace transformers
- `qdrant-client==1.15.1` - Qdrant Python client
- `PyYAML==6.0.1` - YAML parsing (for future frontmatter in MD files)

## Performance Characteristics

### Indexing
- Time: ~10-30 seconds (on first container startup)
- 8 credit card files × ~50-100 chunks each = ~500 vectors
- Stored persistently in Qdrant (`qdrant_data` volume)

### Query
- Embedding: ~5-10ms per query
- Qdrant search: ~1-5ms for 3 results
- Total RAG overhead: ~10-15ms per request

### Scaling
- Current: 8 credit cards (500 vectors)
- At 200 products: ~2500-3000 vectors
- Qdrant can handle millions of vectors efficiently
- Memory usage: ~100MB for 500 vectors, ~500MB for 5000 vectors

## Testing the Implementation

### 1. Check Qdrant Health
```bash
curl http://localhost:6333/health
```

### 2. Check Collection
```python
from qdrant_client import QdrantClient
client = QdrantClient(host="qdrant", port=6333)
collection = client.get_collection("prime_products")
print(f"Points: {collection.points_count}")
```

### 3. Test RAG Retrieval
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the benefits of Islamic credit cards?"}'
```

### 4. Check Logs
```bash
docker logs prime_bot_app | grep RAG
```

## Future Enhancements

### 1. MD Frontmatter + Auto-generation
- Add YAML frontmatter to MD files with metadata
- Auto-generate JSON from MD frontmatter
- Eliminates dual maintenance of JSON + MD

### 2. Multi-Modal Embeddings
- Add tables/images from product PDFs
- Embed structured data alongside text

### 3. Hybrid Search
- BM25 (keyword) + Vector (semantic) search
- Re-rank results with cross-encoders
- Better handling of specific product names/terms

### 4. Caching
- Cache frequently accessed embeddings
- Store popular query results in Redis
- Reduce Qdrant load for common questions

### 5. Continuous Learning
- Track which products users select
- Adjust vector weights for popular products
- A/B test different embedding models

## Troubleshooting

### Issue: "Qdrant connection failed"
**Solution:**
- Ensure Qdrant container is running: `docker ps | grep qdrant`
- Check port: `docker port prime_bot_qdrant`
- Verify network: `docker network ls`

### Issue: "Collection has 0 documents"
**Solution:**
- Check MD file paths exist
- Verify disk space (embeddings are ~300 bytes each)
- Check logs: `docker logs prime_bot_app | grep "RAG: Building"`

### Issue: "No results from RAG"
**Solution:**
- Verify query similarity threshold (hit.score in retrieve)
- Check if collection has points: Use Qdrant check above
- Query might not match any documents semantically

### Issue: Slow embedding generation
**Solution:**
- First startup takes longer (model download + indexing)
- Subsequent requests cached in Qdrant
- Check GPU availability: `nvidia-smi` (if available)

## File Locations Summary

| Component | Location |
|-----------|----------|
| RAG Retriever | `app/services/rag_retriever.py` |
| RAG Enricher | `app/services/rag_enricher.py` |
| Product Matcher (updated) | `app/services/product_matcher.py` |
| Config | `app/core/config.py` |
| Conversation Manager (updated) | `app/core/graphs/conversation_manager.py` |
| Docker Compose | `docker-compose.yml` |
| Requirements | `requirements.txt` |

## Removed Files (Redundant)
- `app/core/knowledge.py` - Replaced by KnowledgeBaseCache
- `app/core/markdown_loader.py` - Replaced by RAGRetriever
- `app/services/knowledge_service.py` - Replaced by KnowledgeBaseCache + RAGRetriever

## Integration Points

### 1. Conversation Manager
- Passes user query to product_matcher_node
- Includes query context in response formatting

### 2. Product Matcher
- Filters products using JSON (fast)
- Optionally enriches with RAG context
- Formats response with semantic information

### 3. Knowledge Cache
- Still provides structured product data (JSON)
- RAG provides unstructured context (MD)
- Complementary, not competing systems

**Methods:**
- `retrieve(query: str, top_k: int)` → Returns top-k relevant chunks with metadata
- `get_instance()` → Singleton access

**Initialization Flow:**
1. Load cached index if exists (FAISS binary + metadata pickle files)
2. If cache miss, build index from all MD files in `app/knowledge/products/`
3. Cache automatically saved for future loads

### 2. RAGEnricher (`app/services/rag_enricher.py`)

High-level service for product-specific Q&A.

**Methods:**
- `enrich_product_response(product_name, query)` → Retrieves relevant context chunk
- `answer_product_question(product_name, query)` → LLM-based answer using RAG context

### 3. Product Matcher Integration

**Updated `format_products_response()` in `app/services/product_matcher.py`:**
- Now accepts `user_query` parameter
- Calls `RAGRetriever.retrieve()` for enrichment
- Augments product response with semantic context

**Usage in `conversation_manager.py`:**
```
product_matcher_node() passes user_query → format_products_response()
```

## Data Flow

### Product Filtering (Existing)
```
User Query → Inquiry Classifier
    ↓
Extract Context (employment, age, income, keywords)
    ↓
JSON-based Filtering (7 criteria)
    ↓
Matched Products
```

### RAG Enrichment (New)
```
Matched Products + User Query
    ↓
RAGRetriever.retrieve(user_query, top_k=3)
    ↓
FAISS Semantic Search
    ↓
Top-K Relevant Chunks with Metadata
    ↓
Response Enrichment (optional product details)
```

## Configuration

**`app/core/config.py`:**
```python
EMBEDDING_MODEL: str = "google/embedding-gemma-300m"
```

Change `EMBEDDING_MODEL` to use different embedders:
- `all-MiniLM-L6-v2` (fast, 384-dim)
- `all-mpnet-base-v2` (slower, 768-dim)

## Vector Index Details

**Location:** `/app/app/knowledge/.rag_cache/`

**Files:**
- `faiss_index.bin` - Binary FAISS index
- `chunks.pkl` - Pickle file with text chunks
- `metadata.pkl` - Pickle file with chunk metadata (file, banking_type, product_type)

**Cache Invalidation:**
- Delete `.rag_cache/` folder to rebuild index
- Automatically rebuilds if missing on startup

## Performance Notes

**Indexing Time:** ~2-5 seconds for all credit card MD files
**Query Time:** ~50-100ms per semantic search
**Memory Footprint:** ~50MB for full credit card index

## Future Enhancements

1. **Multi-Product RAG:** Extend to deposit accounts and schemes
2. **Hybrid Search:** Combine BM25 (keyword) + semantic search
3. **Answer Generation:** Full RAG pipeline with LLM answer synthesis
4. **Reranking:** Use cross-encoder for better ranking of top-k results
5. **Metadata Filtering:** Filter by banking_type during FAISS search

## Dependencies Added

```
faiss-cpu==1.8.0
sentence-transformers==5.1.0
transformers==4.55.2
PyYAML==6.0.1
```

## Migration Notes

**Removed Files (Legacy):**
- `app/core/knowledge.py` - Replaced by `KnowledgeBaseCache`
- `app/core/markdown_loader.py` - Replaced by `RAGRetriever`
- `app/services/knowledge_service.py` - Replaced by `KnowledgeBaseCache`

**Retained Files:**
- `app/services/knowledge_cache.py` - For structured product filtering
- All product JSON files - Used for deterministic filtering

## Testing the RAG Layer

**Basic Test:**
```python
from app.services.rag_retriever import RAGRetriever

rag = RAGRetriever.get_instance()
results = rag.retrieve("lounge access premium benefits", top_k=3)
for r in results:
    print(f"File: {r['metadata']['file']}, Similarity: {r['similarity']}")
    print(f"Chunk: {r['chunk'][:100]}...\n")
```

**Integration Test:**
Query bot: "Show me Islamic cards with lounge access"
Expected: Products returned + RAG context about lounge benefits

## Architecture Decisions

**Why FAISS over PostgreSQL/Vector DB:**
- No external dependency
- In-memory for fast queries
- Easily cacheable to disk
- Sufficient for current scale (50+ products)

**Why sentence-transformers over OpenAI Embeddings:**
- No API cost
- Runs locally
- 300M model balances quality vs speed
- Deterministic results

**Why Chunking:**
- Products are long documents (500+ lines)
- Chunks allow granular retrieval
- Overlap prevents semantic gaps

**Why Singleton Pattern:**
- Model loading is expensive (first run: 1-2 minutes)
- Cache embeddings in memory
- Single instance for entire app lifecycle

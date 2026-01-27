# 💾 CACHING STRATEGY – Knowledge Load & Vector DB

This document specifies how knowledge is loaded, cached, and indexed for fast retrieval.

---

## 1. Overview

### Goals

1. **Fast startup** – Load all docs once at startup
2. **Zero LLM calls for retrieval** – Use vector DB for search
3. **In-process caching** – Keep vector indexes in RAM
4. **Future-proof** – Easy migration to Redis + persistent DB

### Current Stack (Phase 1)

| Layer | Implementation | Persistence |
|-------|---|---|
| Vector DB | In-memory (FAISS or LanceDB) | None (reloaded on restart) |
| Document Cache | Python dict | None |
| Agent Cache | None (not cached) | N/A |
| Session State | In-memory dict or Redis | Redis (if available) |

---

## 2. Knowledge Load Flow

```
Startup
  ↓
Load Markdown Files (from disk)
  ↓
Chunk documents (semantic chunks)
  ↓
Generate embeddings
  ↓
Create FAISS/LanceDB index per domain+vertical
  ↓
Store in KnowledgeIndex (global object)
  ↓
Ready to serve queries
```

### Pseudocode

```python
# app/core/knowledge_loader.py

class KnowledgeIndex:
    def __init__(self):
        self.vectors = {}  # {domain}{vertical} → FAISS index
        self.documents = {}  # {domain}{vertical} → list of Document
        self.metadata = {}  # product_id → metadata dict

    def load(self):
        """Load at startup"""
        # 1. Load all markdown files
        for domain in ["conventional", "islami"]:
            for vertical in ["save", "credit_card"]:
                docs = self._load_markdown_docs(domain, vertical)
                self.documents[f"{domain}_{vertical}"] = docs
                
                # 2. Embed and index
                embeddings = generate_embeddings(docs)
                self.vectors[f"{domain}_{vertical}"] = FAISS.from_documents(docs, embeddings)
                
                # 3. Load metadata from JSON
                self.metadata.update(self._load_json_metadata(domain, vertical))

    def search(self, query: str, domain: str, vertical: str, top_k: int = 3) -> list[Document]:
        """Fast similarity search"""
        index = self.vectors[f"{domain}_{vertical}"]
        return index.similarity_search(query, k=top_k)

# Global instance
knowledge_index = KnowledgeIndex()

@app.on_event("startup")
async def startup_event():
    knowledge_index.load()
    print("✅ Knowledge index loaded")
```

---

## 3. Knowledge Structure

```
app/knowledge/
├── structured/  (JSON metadata for system logic)
│   ├── conventional/
│   │   ├── deposit_accounts.json
│   │   ├── deposit_schemes.json
│   │   └── credit_cards.json
│   └── islami/
│       ├── deposit_accounts.json
│       ├── deposit_schemes.json
│       └── credit_cards.json
│
└── products/  (Markdown docs for RAG/customer info)
    ├── conventional/
    │   ├── save/
    │   │   ├── deposit_accounts/
    │   │   │   ├── prime_first_account.md
    │   │   │   ├── prime_youth_account.md
    │   │   │   └── prime_savings_account.md
    │   │   └── deposit_schemes/
    │   │       ├── prime_kotipoti_dps.md
    │   │       └── prime_fixed_deposit.md
    │   └── credit_card/
    │       ├── platinum_credit_card.md
    │       └── gold_credit_card.md
    └── islami/
        ├── save/
        │   ├── deposit_accounts/
        │   │   ├── prime_hasanah_first_account.md
        │   │   └── prime_hasanah_youth_account.md
        │   └── deposit_schemes/
        │       ├── mudaraba_dps.md
        │       └── monthly_income_scheme.md
        └── credit_card/
            └── islami_credit_card.md
```

---

## 4. Embedding Strategy

### Embedding Model

Use: **Sentence-Transformers** (`all-MiniLM-L6-v2`)

- Fast (inference < 100ms)
- Good for finance domain
- No API calls needed (open source)

### Chunking Strategy

**Semantic chunking** (not fixed-size):

```python
# app/core/chunker.py

def chunk_markdown(doc: str, max_chunk_size: int = 500) -> list[str]:
    """
    Split markdown by semantic boundaries:
    - Headings
    - Paragraphs
    - Tables
    """
    chunks = []
    current = ""
    
    lines = doc.split('\n')
    for line in lines:
        if line.startswith('#'):
            # New section
            if current:
                chunks.append(current.strip())
            current = line
        else:
            current += '\n' + line
            
        if len(current) > max_chunk_size:
            chunks.append(current.strip())
            current = ""
    
    if current:
        chunks.append(current.strip())
    
    return chunks
```

---

## 5. Vector DB Implementation

### Option A: FAISS (Recommended for Testing)

```python
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Load embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Create index from documents
vectorstore = FAISS.from_documents(documents, embeddings)

# Search
results = vectorstore.similarity_search("Can I open Prime First Account?", k=3)
```

### Option B: LanceDB (Alternative, slightly better for scaling)

```python
import lancedb

db = lancedb.connect("./lancedb")
table = db.create_table("documents", data=documents)

# Search
results = table.search("Can I open Prime First Account?").limit(3).to_list()
```

---

## 6. Per-Agent Vector Indexes

Each agent has its own **focused index**:

```python
class KnowledgeIndex:
    def __init__(self):
        self.indexes = {
            "conventional_save": FAISS(...),
            "conventional_credit_card": FAISS(...),
            "islami_save": FAISS(...),
            "islami_credit_card": FAISS(...),
        }

    def search_for_agent(self, query: str, domain: str, vertical: str) -> list[Document]:
        """Search only the relevant index"""
        key = f"{domain}_{vertical}"
        return self.indexes[key].similarity_search(query, k=5)
```

**Benefits:**
- Fast (no filtering after search)
- Accurate (only relevant docs returned)
- Scalable (can add more indexes)

---

## 7. Metadata Caching

### JSON Metadata in Memory

```python
class KnowledgeIndex:
    def __init__(self):
        self.metadata = {}  # {product_id: product_metadata}
    
    def load_metadata(self):
        """Load all JSON files into memory"""
        for domain in ["conventional", "islami"]:
            for vertical in ["save", "credit_card"]:
                path = f"knowledge/structured/{domain}/{vertical}.json"
                with open(path) as f:
                    products = json.load(f)
                    self.metadata.update(products)
    
    def get_product(self, product_id: str) -> dict:
        """O(1) lookup"""
        return self.metadata[product_id]
```

---

## 8. Session State Caching

### In-Memory Store (For Testing)

```python
# app/core/session_store.py

class SessionStore:
    def __init__(self):
        self.sessions = {}  # {session_id: ConversationState}
    
    def get(self, session_id: str) -> ConversationState:
        return self.sessions.get(session_id)
    
    def save(self, state: ConversationState):
        self.sessions[state.session_id] = state

session_store = SessionStore()
```

### Redis Store (For Production)

```python
import redis

class RedisSessionStore:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.client = redis.from_url(url)
    
    def get(self, session_id: str) -> ConversationState:
        data = self.client.get(f"session:{session_id}")
        if data:
            return ConversationState.parse_raw(data)
        return None
    
    def save(self, state: ConversationState):
        self.client.setex(
            f"session:{state.session_id}",
            ex=86400,  # 24 hours TTL
            value=state.json()
        )
```

---

## 9. Startup Sequence

```python
# app/main.py

from fastapi import FastAPI
from app.core.knowledge_loader import knowledge_index
from app.core.session_store import session_store

app = FastAPI()

@app.on_event("startup")
async def startup():
    print("🔄 Loading knowledge index...")
    knowledge_index.load()
    print(f"✅ Loaded {len(knowledge_index.metadata)} products")
    
    print("🔄 Initializing session store...")
    # session_store is ready (in-memory)
    
    print("✅ Chatbot ready!")
```

---

## 10. Migration Path

### Phase 1 (Current)
- In-memory FAISS
- In-memory session store
- JSON metadata cached

### Phase 2 (Production)
- FAISS with disk persistence
- Redis for session store
- Product metadata in PostgreSQL

### Phase 3 (Scale)
- Distributed FAISS (Vespa or Weaviate)
- Redis cluster
- CDC from PostgreSQL → Vector DB

---

## 11. Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Load all docs | ~2-5s | One-time at startup |
| Embed query | ~50ms | Sentence-Transformers |
| Vector search | ~10ms | FAISS |
| Metadata lookup | <1ms | In-memory dict |
| Session save (memory) | <1ms | Dict write |
| Session save (Redis) | ~5ms | Network + serialization |

---

## 12. Memory Footprint

| Component | Size | Notes |
|-----------|------|-------|
| FAISS indexes (4x) | ~50-100 MB | 50-100 products × 384-dim embeddings |
| Document store | ~5-10 MB | Text only |
| Metadata (JSON) | ~1-2 MB | Product attributes |
| Session store | 1-10 MB | Depends on active sessions |
| **Total** | **~60-120 MB** | Easily fits in memory |

---

## 13. Testing

```python
# tests/test_knowledge_loader.py

def test_knowledge_index_loads():
    index = KnowledgeIndex()
    index.load()
    assert len(index.metadata) > 0
    assert "conventional_save" in index.indexes

def test_search_returns_documents():
    index = KnowledgeIndex()
    index.load()
    results = index.search_for_agent(
        "eligibility for Prime First Account",
        domain="conventional",
        vertical="save"
    )
    assert len(results) > 0

def test_metadata_lookup_is_fast():
    index = KnowledgeIndex()
    index.load()
    
    import time
    start = time.time()
    for _ in range(10000):
        index.get_product("prime_first_account")
    elapsed = time.time() - start
    
    assert elapsed < 100  # 10ms avg
```


# Prime Bot - Folder Structure & Responsibilities

## 📁 Architecture Overview

```
app/
├── core/                          # Infrastructure & Dependencies
│   ├── config.py                 # Settings, environment variables
│   ├── redis.py                  # Redis client initialization
│   ├── intent_detector.py        # OpenAI intent detection
│   ├── knowledge.py              # JSON knowledge base loader
│   ├── markdown_loader.py        # Markdown document loader
│   └── graphs/                   # LangGraph state machines (6 graphs)
│
├── services/                      # Business Logic & Domain Services
│   ├── conversation_manager.py   # Redis state management for sessions
│   ├── knowledge.py              # Knowledge base queries & filtering
│   ├── user_info.py              # User profile extraction & enrichment
│   ├── response_builder.py       # Response generation logic
│   └── [other domain services]
│
├── api/                           # FastAPI Routes & Endpoints
│   └── chat.py                   # Main conversation endpoint (/chat)
│
├── models/                        # Pydantic data models
│   ├── conversation_state.py     # ConversationState, UserProfile
│   ├── intent.py                 # IntentResult, enums
│   └── state.py                  # State models
│
├── prompts/                       # LLM Prompts (1 file = 1 prompt)
│   ├── intent_detection.py
│   ├── eligibility_check.py
│   ├── product_recommendation.py
│   ├── response_generation.py
│   └── [other prompts]
│
├── knowledge/                     # External Knowledge Base
│   ├── structured/               # Structured data (JSON)
│   │   ├── conventional/
│   │   │   ├── credit_cards.json
│   │   │   ├── deposit_accounts.json
│   │   │   └── deposit_schemes.json
│   │   └── islami/
│   │       ├── credit_cards.json
│   │       ├── deposit_accounts.json
│   │       └── deposit_schemes.json
│   └── products/                 # Human-readable data (Markdown)
│       ├── conventional/
│       │   ├── credit/
│       │   └── save/
│       └── islami/
│           ├── credit/
│           └── save/
│
└── main.py                        # FastAPI app initialization
```

## 🎯 File Classification

### ✅ KEEP in `app/core/` (Infrastructure Layer)
| File | Purpose | Reason |
|------|---------|--------|
| `config.py` | Load environment variables & settings | Infrastructure dependency |
| `redis.py` | Redis connection & client | Infrastructure dependency |
| `intent_detector.py` | OpenAI API integration for intent detection | Core service, reusable |
| `knowledge.py` | Load JSON from /knowledge/structured | Core data access |
| `markdown_loader.py` | Load markdown from /knowledge/products | Core data access |
| `graphs/` | 6 LangGraph state machines | Core orchestration |

### ✅ KEEP in `app/services/` (Business Logic Layer)
| File | Purpose | Reason |
|------|---------|--------|
| `conversation_manager.py` | Manage conversation state in Redis | Business logic, domain-specific |
| `knowledge.py` | Query & filter knowledge base | Business logic |
| `user_info.py` | Extract & enrich user profile | Business logic |
| `response_builder.py` | Build contextual responses | Business logic |

### ✅ KEEP in `app/api/` (API Routes)
| File | Purpose |
|------|---------|
| `chat.py` | Main `/api/chat` endpoint |

### ❌ DELETED
- `app/api/knowledge.py` - **Duplicate stub with no real implementation**

### ✅ KEEP in `app/prompts/` (LLM Prompts)
1 file = 1 prompt - separated for easy maintenance

## 🔄 Data Flow

```
User Message
    ↓
chat.py (API) ← imports from
    ├→ core/intent_detector.py (What does user want?)
    ├→ services/user_info.py (Extract age, employment, etc.)
    ├→ services/knowledge.py (Query knowledge base)
    ├→ services/conversation_manager.py (Load/save state)
    └→ services/response_builder.py (Build response)
    ↓
Response to User
```

## 📝 Import Guidelines

### In `app/api/chat.py` (Routes):
```python
from app.core.intent_detector import IntentDetector
from app.services.conversation_manager import ConversationManager
from app.services.knowledge import KnowledgeQueryService
from app.services.user_info import extract_user_info
from app.services.response_builder import ResponseBuilder
```

### In `app/services/*.py` (Business Logic):
```python
from app.core.knowledge import KnowledgeBase
from app.core.redis import get_redis
from app.core.config import settings
```

### Never import:
❌ `from app.api import ...` (Routes shouldn't import routes)
❌ `from app.services import ...` in core (Core shouldn't depend on business logic)

## 🚀 Next Steps

1. ✅ Removed duplicate `app/api/knowledge.py`
2. ✅ Moved `app/core/conversation.py` → `app/services/conversation_manager.py`
3. ✅ Core now contains only infrastructure
4. ✅ Services contain all business logic
5. 🔄 API routes are lean and focused

Structure is now clean and follows Clean Architecture principles!

# 🏗️ MODELS SPECIFICATION – Pydantic Control Plane

This document specifies all Pydantic models that control the chatbot system. These are the **contracts** between modules.

---

## Directory Structure

```
app/models/
├── __init__.py
├── api.py          # Request/response schemas
├── intent.py       # Intent detection models
├── state.py        # Conversation state
├── agent.py        # Agent output schemas
└── error.py        # Error models
```

---

## 1. API Models (`app/models/api.py`)

### ChatRequest

```python
from pydantic import BaseModel
from typing import Literal, Optional

class ChatRequest(BaseModel):
    session_id: str
    user_message: str
    channel: Literal["web", "mobile"]
    language: Literal["en", "bn"] = "en"

    class Config:
        example = {
            "session_id": "sess_abc123",
            "user_message": "Can I open Prime First Account?",
            "channel": "web",
            "language": "en"
        }
```

### ChatResponse

```python
class ChatResponse(BaseModel):
    message: str
    domain: Optional[str] = None
    vertical: Optional[str] = None
    agent: str
    sources: list[str] = []
    confidence: float
    refusal: bool = False

    class Config:
        example = {
            "message": "Yes, you can open Prime First Account.",
            "domain": "conventional",
            "vertical": "save",
            "agent": "eligibility_graph",
            "sources": ["prime_first_account.md"],
            "confidence": 0.95,
            "refusal": False
        }
```

---

## 2. Intent Models (`app/models/intent.py`)

### IntentResult

LLM must output this schema or request fails.

```python
from pydantic import BaseModel
from typing import Literal, Optional

class IntentResult(BaseModel):
    domain: Optional[Literal["conventional", "islami", "nrb"]] = None
    vertical: Optional[Literal["save", "credit_card", "debit"]] = None
    intent_type: Optional[Literal["eligibility", "explore", "compare", "explain"]] = None
    confidence: float  # 0.0–1.0
    extracted_entities: dict = {}

    class Config:
        example = {
            "domain": "conventional",
            "vertical": "save",
            "intent_type": "eligibility",
            "confidence": 0.92,
            "extracted_entities": {
                "product_name": "Prime First Account",
                "age": 16,
                "deposit": 5000
            }
        }
```

### IntentDefinition

Defines valid intent types for the system.

```python
class IntentDefinition(BaseModel):
    intent_type: str
    description: str
    examples: list[str]

    class Config:
        example = {
            "intent_type": "eligibility",
            "description": "User wants to check if they can open/use a product",
            "examples": [
                "Can I open this account?",
                "Am I eligible for this card?",
                "What are the requirements?"
            ]
        }
```

---

## 3. Conversation State Models (`app/models/state.py`)

### ConversationState

Main state object. Stored in Redis or in-memory cache.

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserProfile(BaseModel):
    age: Optional[int] = None
    banking_type: Optional[str] = None  # "islami" | "conventional"
    employment_type: Optional[str] = None  # "salaried" | "self_employed" | "student" | "retired"
    income: Optional[float] = None  # Monthly income in BDT
    income_verified: bool = False
    deposit: Optional[float] = None  # Initial deposit in BDT
    credit_score: Optional[int] = None  # For credit cards
    
    class Config:
        example = {
            "age": 25,
            "banking_type": "conventional",
            "employment_type": "salaried",
            "income": 50000,
            "income_verified": True,
            "deposit": 5000,
            "credit_score": 750
        }


class ConversationState(BaseModel):
    session_id: str
    user_profile: UserProfile = UserProfile()
    
    # Intent & routing
    detected_domain: Optional[str] = None  # "conventional" | "islami" | "nrb"
    detected_vertical: Optional[str] = None  # "save" | "credit_card" | "debit"
    detected_intent: Optional[str] = None  # "eligibility" | "explore" | "compare" | "explain"
    
    # Context
    product_name: Optional[str] = None
    comparison_products: list[str] = []
    missing_slots: list[str] = []
    
    # Conversation flow
    turn_count: int = 0
    last_agent: Optional[str] = None
    last_response: Optional[str] = None
    
    # Metadata
    created_at: datetime
    last_updated: datetime
    channel: str = "web"
    language: str = "en"

    class Config:
        example = {
            "session_id": "sess_abc123",
            "user_profile": {
                "age": 20,
                "banking_type": "conventional",
                "employment_type": "student",
                "deposit": 1000
            },
            "detected_domain": "conventional",
            "detected_vertical": "save",
            "detected_intent": "eligibility",
            "product_name": "Prime First Account",
            "missing_slots": ["age", "initial_deposit"],
            "turn_count": 2,
            "last_agent": "eligibility_graph",
            "created_at": "2026-01-27T10:30:00",
            "last_updated": "2026-01-27T10:32:00"
        }
```

---

## 4. Agent Output Models (`app/models/agent.py`)

### AgentAnswer

Standard output for all agents. No free-text beyond this.

```python
from pydantic import BaseModel
from typing import Optional

class AgentAnswer(BaseModel):
    answer: str  # Response text
    sources: list[str]  # File paths or doc IDs used
    refusal: bool = False  # Whether request was refused
    confidence: float  # 0.0–1.0
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None

    class Config:
        example = {
            "answer": "Yes, a 16-year-old can open Prime First Account.",
            "sources": ["knowledge/products/conventional/save/deposit_accounts/prime_first_account.md"],
            "refusal": False,
            "confidence": 0.95,
            "requires_clarification": False
        }
```

### EligibilityResult

Output from eligibility_graph.

```python
class EligibilityResult(AgentAnswer):
    is_eligible: bool
    eligibility_reason: str
    missing_criteria: list[str] = []

    class Config:
        example = {
            "answer": "You are eligible for Prime First Account.",
            "sources": ["prime_first_account.md"],
            "is_eligible": True,
            "eligibility_reason": "Age (16) >= minimum (13) and deposit (5000) >= minimum (1000)",
            "missing_criteria": [],
            "confidence": 0.98
        }
```

### ComparisonResult

Output from comparison_graph.

```python
class ComparisonResult(AgentAnswer):
    products_compared: list[str]
    comparison_summary: dict
    constraint_violations: list[str] = []

    class Config:
        example = {
            "answer": "Prime First Account has lower eligibility (age 13+) vs Prime Youth (age 18+).",
            "sources": ["product1.md", "product2.md"],
            "products_compared": ["Prime First Account", "Prime Youth Account"],
            "comparison_summary": {
                "min_age": {"Prime First": 13, "Prime Youth": 18},
                "min_balance": {"Prime First": 1000, "Prime Youth": 500}
            },
            "constraint_violations": [],
            "confidence": 0.88
        }
```

### ExplainResult

Output from explain_graph (RAG-based).

```python
class ExplainResult(AgentAnswer):
    explanation_type: str  # "feature" | "process" | "eligibility" | "fee"
    related_products: list[str] = []

    class Config:
        example = {
            "answer": "Prime First Account includes free ATM access, monthly statements, and multi-currency support.",
            "sources": ["prime_first_account.md"],
            "explanation_type": "feature",
            "related_products": ["Prime Youth Account", "Prime Savings Account"],
            "confidence": 0.92
        }
```

---

## 5. Error Models (`app/models/error.py`)

### ErrorResponse

```python
from pydantic import BaseModel
from typing import Optional

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict] = None

    class Config:
        example = {
            "error_code": "INTENT_LOW_CONFIDENCE",
            "message": "Could you please clarify what you want to know?"
        }
```

### ValidationError

```python
class ValidationErrorDetail(BaseModel):
    field: str
    error: str

class ValidationErrorResponse(ErrorResponse):
    errors: list[ValidationErrorDetail]

    class Config:
        example = {
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors": [
                {"field": "user_message", "error": "Field required"}
            ]
        }
```

---

## 6. Product Models

### Product (Core Product Definition)

```python
class Product(BaseModel):
    product_id: str
    product_name: str
    domain: str  # "conventional" | "islami"
    vertical: str  # "save" | "credit_card" | "debit"
    category: str  # "savings_account" | "dps" | "fdr" | etc.

class ProductMetadata(Product):
    """Extended with system metadata for eligibility checks"""
    min_age: int
    max_age: Optional[int] = None
    min_balance: float
    income_required: bool
    employment_types: Optional[list[str]] = None
    credit_score_required: bool = False
    features: list[str] = []
    markdown_ref: str
    json_ref: str

    class Config:
        example = {
            "product_id": "prime_first_account",
            "product_name": "Prime First Account",
            "domain": "conventional",
            "vertical": "save",
            "category": "savings_account",
            "min_age": 13,
            "max_age": None,
            "min_balance": 1000,
            "income_required": False,
            "employment_types": None,
            "features": ["low_minimum", "student_eligible"],
            "markdown_ref": "knowledge/products/conventional/save/deposit_accounts/prime_first_account.md",
            "json_ref": "knowledge/structured/conventional/deposit_accounts.json"
        }
```

---

## 7. Slot Definition

### Slot

Represents an extractable entity.

```python
class Slot(BaseModel):
    name: str  # e.g., "product_name", "user_age"
    type: str  # "string" | "int" | "float" | "enum"
    required: bool
    context: str  # When this slot is required

    class Config:
        example = {
            "name": "product_name",
            "type": "string",
            "required": False,
            "context": "Optional for explore; required for eligibility"
        }
```

---

## 8. Import Pattern

```python
# In your FastAPI app:

from app.models.api import ChatRequest, ChatResponse
from app.models.intent import IntentResult
from app.models.state import ConversationState
from app.models.agent import AgentAnswer, EligibilityResult
from app.models.error import ErrorResponse
```

---

## 9. Type Safety Throughout

Every module uses these models:

- `intent_detector.py` → Returns `IntentResult`
- `eligibility_graph.py` → Returns `EligibilityResult`
- `comparison_graph.py` → Returns `ComparisonResult`
- `explain_graph.py` → Returns `ExplainResult`
- `chat.py` endpoint → Accepts `ChatRequest`, returns `ChatResponse`

**Result:** Type-safe pipeline with zero silent failures.


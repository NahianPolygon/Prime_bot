# 🚨 ERROR HANDLING – Comprehensive Strategy

Banks do NOT allow silent failures. Every error must be handled, logged, and communicated clearly to users.

---

## 1. Error Categories

### Error Types

| Error | HTTP | Cause | User Action |
|-------|------|-------|------------|
| **ValidationError** | 400 | Bad request format | Resend correct JSON |
| **IntentError** | 200 + refusal | Low confidence intent | Clarify question |
| **SlotExtractionError** | 200 + clarification | Missing required slots | Provide missing info |
| **RetrievalError** | 200 + fallback | Knowledge not found | Try different question |
| **AgentError** | 500 | LLM/graph failure | System error message |
| **PolicyViolation** | 200 + refusal | Restricted question | Explain policy |
| **StateError** | 500 | Session state corruption | Restart conversation |
| **RateLimitError** | 429 | Too many requests | Wait and retry |

---

## 2. Error Response Schemas

### Standard Error Response

```python
from pydantic import BaseModel
from typing import Optional

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict] = None
    timestamp: str  # ISO 8601

    class Config:
        example = {
            "error_code": "INTENT_LOW_CONFIDENCE",
            "message": "Could you please clarify what you want to know?",
            "timestamp": "2026-01-27T10:30:45Z"
        }
```

### Validation Error Response

```python
class ValidationErrorResponse(BaseModel):
    error_code: str = "VALIDATION_ERROR"
    message: str
    errors: list[dict]
    timestamp: str

    class Config:
        example = {
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors": [
                {"field": "session_id", "error": "Field required"},
                {"field": "user_message", "error": "String must have at least 1 character"}
            ],
            "timestamp": "2026-01-27T10:30:45Z"
        }
```

---

## 3. Error Code Reference

### 400-Level Errors (Client Errors)

| Code | HTTP | Message | Action |
|------|------|---------|--------|
| `VALIDATION_ERROR` | 400 | Invalid request JSON | Retry with valid JSON |
| `MISSING_FIELD` | 400 | Required field missing | Add missing field |
| `INVALID_ENUM` | 400 | Invalid enum value | Use valid value |
| `INVALID_TYPE` | 400 | Wrong data type | Correct the type |
| `SESSION_NOT_FOUND` | 400 | Session doesn't exist | Create new session |

---

### 200-Level Errors (Handled Gracefully)

| Code | HTTP | Message | User See | Action |
|-------|------|---------|----------|--------|
| `INTENT_LOW_CONFIDENCE` | 200 | Unclear question | Clarification prompt | Ask user to clarify |
| `MISSING_SLOTS` | 200 | Required info missing | Question for missing slot | Collect info in next turn |
| `NO_PRODUCTS_FOUND` | 200 | No matching products | "No products match..." | Try different criteria |
| `POLICY_VIOLATION` | 200 + refusal | Restricted comparison | Explain policy | Offer alternative |

---

### 500-Level Errors (Server Errors)

| Code | HTTP | Message | User See | Action |
|------|------|---------|----------|--------|
| `AGENT_ERROR` | 500 | Graph/LLM failure | "Something went wrong" | Log error, retry |
| `STATE_CORRUPTION` | 500 | Session state invalid | "Session expired" | Start new session |
| `KNOWLEDGE_LOAD_FAILURE` | 500 | Can't load docs | "System unavailable" | Restart server |
| `EMBEDDING_ERROR` | 500 | Vector DB failure | "Searching failed" | Check vector DB |

---

### 429-Level Errors (Rate Limiting)

| Code | HTTP | Message | Retry After |
|------|------|---------|-------------|
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Return `Retry-After` header |

---

## 4. Per-Module Error Handling

### A. Intent Detection (`intent_detector.py`)

```python
from app.models.error import ErrorResponse
from app.models.intent import IntentResult

def detect_intent(user_message: str) -> IntentResult | ErrorResponse:
    """
    Detect intent from user message.
    
    Returns:
    - IntentResult with high confidence → proceed
    - IntentResult with low confidence → ask clarification
    - ErrorResponse on critical failure
    """
    
    try:
        # Use LLM to detect intent
        result = llm.detect_intent(user_message)
        
        # Validate result
        intent = IntentResult(**result)
        
        if intent.confidence < 0.5:
            # Low confidence → clarification
            return ChatResponse(
                message="I'm not sure what you're asking. Are you looking for:\n• Eligibility check?\n• Product comparison?\n• Feature explanation?",
                agent="intent_detector",
                confidence=intent.confidence,
                refusal=False
            )
        
        return intent
    
    except ValueError as e:
        # LLM returned invalid schema
        return ErrorResponse(
            error_code="INTENT_PARSING_ERROR",
            message="Could not understand your question. Please try rephrasing.",
            details={"error": str(e)}
        )
    
    except Exception as e:
        # Unexpected error
        logging.error(f"Intent detection failed: {str(e)}")
        return ErrorResponse(
            error_code="AGENT_ERROR",
            message="System error occurred. Please try again.",
            details={"error": str(e)}
        )
```

---

### B. Slot Extraction (`intent_detector.py`)

```python
def extract_slots(user_message: str) -> dict | ErrorResponse:
    """
    Extract slots from user message using LLM.
    """
    
    try:
        # Use LLM to extract
        slots = llm.extract_slots(user_message)
        
        # Validate each slot
        extracted = ExtractedSlots(**slots)
        return extracted.dict(exclude_none=True)
    
    except ValidationError as e:
        # Invalid slot value
        return ChatResponse(
            message=f"I couldn't understand that. {e.errors()[0]['msg']}",
            agent="slot_extractor",
            confidence=0.0,
            refusal=False
        )
    
    except Exception as e:
        logging.error(f"Slot extraction failed: {str(e)}")
        return ErrorResponse(
            error_code="SLOT_EXTRACTION_ERROR",
            message="Could not parse your request. Please try again.",
            details={"error": str(e)}
        )
```

---

### C. Eligibility Graph (`graphs/eligibility_graph.py`)

```python
def eligibility_graph(state: ConversationState) -> EligibilityResult | ErrorResponse:
    """
    Check user eligibility for a product.
    """
    
    try:
        # Get product metadata
        product = knowledge_index.get_product(state.product_name)
        if not product:
            return ChatResponse(
                message=f"I couldn't find '{state.product_name}'. Could you spell it out?",
                agent="eligibility_graph",
                confidence=0.0,
                refusal=False
            )
        
        # Check eligibility
        user = state.user_profile
        eligible = (
            user.age >= product.min_age and
            (product.max_age is None or user.age <= product.max_age) and
            user.deposit >= product.min_balance
        )
        
        if eligible:
            return EligibilityResult(
                answer=f"Yes, you are eligible for {product.product_name}.",
                sources=[product.markdown_ref],
                is_eligible=True,
                eligibility_reason=f"Meets all criteria",
                confidence=0.95
            )
        else:
            missing = []
            if user.age < product.min_age:
                missing.append(f"Age must be at least {product.min_age}")
            if user.deposit < product.min_balance:
                missing.append(f"Minimum deposit is ৳{product.min_balance}")
            
            return EligibilityResult(
                answer=f"You are not currently eligible for {product.product_name}.",
                sources=[product.markdown_ref],
                is_eligible=False,
                missing_criteria=missing,
                confidence=0.95
            )
    
    except KeyError:
        return ChatResponse(
            message="Product not found in system.",
            agent="eligibility_graph",
            confidence=0.0,
            refusal=False
        )
    
    except Exception as e:
        logging.error(f"Eligibility check failed: {str(e)}")
        return ErrorResponse(
            error_code="AGENT_ERROR",
            message="Could not check eligibility. Please try again.",
            details={"error": str(e)}
        )
```

---

### D. Comparison Graph (`graphs/comparison_graph.py`)

```python
def comparison_graph(state: ConversationState) -> ComparisonResult | ErrorResponse:
    """
    Compare multiple products with constraint checking.
    """
    
    try:
        products = state.comparison_products
        
        if len(products) < 2:
            return ChatResponse(
                message="I need at least 2 products to compare. Which ones would you like?",
                agent="comparison_graph",
                confidence=0.0,
                refusal=False
            )
        
        # Check cross-domain constraints
        domains = set(p.domain for p in products)
        
        if len(domains) > 1:
            comparison_type = detect_comparison_type(state.last_message)
            
            if not check_comparison_constraints(
                domain1=list(domains)[0],
                domain2=list(domains)[1],
                comparison_type=comparison_type
            ):
                return ComparisonResult(
                    answer="I cannot compare profit/return across Islami and conventional products. I can explain each separately.",
                    sources=[],
                    products_compared=products,
                    constraint_violations=["CROSS_DOMAIN_NUMERIC_COMPARISON"],
                    confidence=1.0,
                    refusal=True
                )
        
        # Generate comparison
        # (code continues...)
    
    except Exception as e:
        logging.error(f"Comparison failed: {str(e)}")
        return ErrorResponse(
            error_code="AGENT_ERROR",
            message="Could not compare products. Please try again.",
            details={"error": str(e)}
        )
```

---

## 5. API Endpoint Error Handling

```python
# app/api/chat.py

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint with comprehensive error handling.
    """
    
    try:
        # 1. Validate request
        # (Pydantic handles this automatically)
        
        # 2. Get or create session
        state = session_store.get(request.session_id)
        if state is None:
            state = ConversationState(
                session_id=request.session_id,
                created_at=datetime.now(),
                last_updated=datetime.now(),
                channel=request.channel,
                language=request.language
            )
        
        # 3. Detect intent
        intent = await intent_detector.detect_intent(request.user_message)
        
        if isinstance(intent, ErrorResponse):
            return intent  # Return error to user
        
        state.detected_intent = intent.intent_type
        state.detected_domain = intent.domain
        state.detected_vertical = intent.vertical
        
        # 4. Extract slots
        slots = await intent_detector.extract_slots(request.user_message)
        state.missing_slots = get_missing_slots(slots, intent.intent_type)
        
        # 5. Route to agent
        if intent.intent_type == "eligibility":
            result = await eligibility_graph(state)
        elif intent.intent_type == "compare":
            result = await comparison_graph(state)
        else:
            result = await explain_graph(state)
        
        # 6. Handle agent results
        if isinstance(result, ErrorResponse):
            logging.error(f"Agent error: {result.error_code}")
            return ChatResponse(
                message=result.message,
                agent="error_handler",
                confidence=0.0,
                refusal=True
            )
        
        # 7. Save state and return
        state.last_response = result.answer
        state.last_agent = result.agent
        state.turn_count += 1
        state.last_updated = datetime.now()
        
        session_store.save(state)
        
        return ChatResponse(
            message=result.answer,
            domain=state.detected_domain,
            vertical=state.detected_vertical,
            agent=result.agent,
            sources=result.sources,
            confidence=result.confidence,
            refusal=result.refusal
        )
    
    except HTTPException as e:
        # Re-raise FastAPI HTTPExceptions
        raise e
    
    except ValidationError as e:
        # Pydantic validation error
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": [
                    {"field": err["loc"][0], "error": err["msg"]}
                    for err in e.errors()
                ]
            }
        )
    
    except Exception as e:
        # Unexpected error
        logging.critical(f"Unhandled error in chat endpoint: {str(e)}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "AGENT_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "timestamp": datetime.now().isoformat()
            }
        )

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors": [
                {
                    "field": ".".join(str(x) for x in err["loc"]),
                    "error": err["msg"]
                }
                for err in exc.errors()
            ]
        }
    )
```

---

## 6. Logging Strategy

```python
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging for production
logHandler = logging.FileHandler('chatbot.log')
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Logging patterns
logging.info("Chat started", extra={"session_id": "sess_123", "user_message": msg})
logging.warning("Low confidence intent", extra={"confidence": 0.35, "message": msg})
logging.error("Agent failed", extra={"error_code": "AGENT_ERROR", "agent": "eligibility_graph"})
logging.critical("System failure", extra={"error": str(e)})
```

---

## 7. Testing Error Handling

```python
# tests/test_error_handling.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_validation_error_missing_field():
    """Missing required field → 400"""
    response = client.post("/api/chat", json={
        "session_id": "sess_123"
        # Missing: user_message, channel
    })
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"

def test_intent_low_confidence():
    """Low confidence intent → 200 + clarification"""
    response = client.post("/api/chat", json={
        "session_id": "sess_123",
        "user_message": "something",  # Unclear
        "channel": "web"
    })
    assert response.status_code == 200
    data = response.json()
    assert "clarif" in data["message"].lower()

def test_product_not_found():
    """Unknown product → graceful error"""
    response = client.post("/api/chat", json={
        "session_id": "sess_123",
        "user_message": "Can I open Nonexistent Account?",
        "channel": "web"
    })
    assert response.status_code == 200
    data = response.json()
    assert "could not find" in data["message"].lower()

def test_policy_violation_cross_domain_roi():
    """Comparing Islami + Conventional ROI → refusal"""
    response = client.post("/api/chat", json={
        "session_id": "sess_123",
        "user_message": "Which earns more, Mudaraba DPS or conventional FDR?",
        "channel": "web"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["refusal"] == True
    assert "cannot compare" in data["message"].lower()
```

---

## 8. Error Monitoring

### Metrics to Track

```python
# Use OpenTelemetry or similar
error_counter = Counter(
    "chatbot_errors_total",
    "Total errors by type",
    ["error_code"]
)

# In error handlers:
error_counter.labels(error_code="INTENT_LOW_CONFIDENCE").inc()
error_counter.labels(error_code="POLICY_VIOLATION").inc()
error_counter.labels(error_code="AGENT_ERROR").inc()
```

### Alerting Rules

- **CRITICAL:** Server errors (5xx) → Page on-call engineer
- **HIGH:** Policy violations (3+ in 5 min) → Log and review
- **MEDIUM:** Low confidence intents (5+ in session) → Track user experience
- **LOW:** Validation errors → No action (user fault)

---

## 9. Fallback Strategies

### Strategy: Graceful Degradation

If comparison fails → Offer individual product explanations:
```
"I couldn't generate a full comparison. I can explain each product separately. Which one would you like to know about?"
```

### Strategy: Clarification Loop

If intent is unclear:
```
"I'm not sure what you want. Are you asking about:
1️⃣ Eligibility (Can I open this?)
2️⃣ Features (What do I get?)
3️⃣ Comparison (Which is better?)
4️⃣ Explanation (How does it work?)
```

### Strategy: Knowledge Fallback

If specific doc not found:
```
"I don't have detailed info on that. I can suggest similar products or general account types. What would help?"
```


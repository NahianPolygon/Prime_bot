# 🧪 TESTING STRATEGY – LangFuse Observability + Unit Tests

This document covers **how to test the banking chatbot** using:
1. **LangFuse** - Observability & tracing for LangGraph agents
2. **pytest** - Unit testing for models, logic, and knowledge
3. **Integration Tests** - End-to-end API testing
4. **Load Testing** - Performance validation

---

## 1. 🔍 LangFuse Observability

### What is LangFuse?

LangFuse is an **open-source LLM observability platform** designed for LangChain/LangGraph applications.

**Key Benefits:**
- ✅ Trace every LLM call (prompts, completions, costs)
- ✅ Monitor agent routing decisions
- ✅ Track conversation flow across multiple agents
- ✅ Identify where chatbot fails (intent detection, eligibility, etc.)
- ✅ Measure latency per step
- ✅ Debug complex multi-agent workflows

---

### Installation

```bash
pip install langfuse
```

### Setup (in your FastAPI app)

**File:** `app/core/langfuse_client.py`

```python
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
import os

# Initialize Langfuse
langfuse_client = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

# Create callback handler for LangGraph
def get_langfuse_callback():
    """Returns LangFuse callback for tracing"""
    return CallbackHandler(
        user_id="user_prime_bot",
        session_id="session_prime_bot",
        tags=["banking_chatbot", "production"],
    )

# For testing: flush data before shutdown
async def shutdown_langfuse():
    """Flush pending traces on app shutdown"""
    langfuse_client.flush()
```

**Environment Variables (.env):**

```bash
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

### Tracing LangGraph Agents

**File:** `app/core/router.py`

```python
from langfuse.callback import CallbackHandler
from langfuse_client import get_langfuse_callback

async def route_to_agent(intent_result: IntentResult, user_message: str):
    """Route to correct agent with LangFuse tracing"""
    
    # Get LangFuse callback
    callback = get_langfuse_callback()
    
    # Determine domain and vertical
    domain = intent_result.domain  # "conventional" or "islami"
    vertical = intent_result.vertical  # "save" or "credit"
    
    # LangFuse trace
    callback.on_chain_start(
        serialized={"name": f"{domain}_{vertical}_agent"},
        inputs={"user_message": user_message, "intent": intent_result.dict()}
    )
    
    try:
        # Call appropriate agent
        if domain == "conventional" and vertical == "save":
            response = await conventional_save_agent.invoke(
                {"user_message": user_message, "intent": intent_result},
                callbacks=[callback]  # <-- Pass callback to agent
            )
        elif domain == "islami" and vertical == "credit":
            response = await islami_credit_agent.invoke(
                {"user_message": user_message, "intent": intent_result},
                callbacks=[callback]
            )
        # ... more conditions
        
        callback.on_chain_end(outputs={"response": response.message})
        return response
        
    except Exception as e:
        callback.on_chain_error(error=str(e))
        raise
```

---

### What LangFuse Tracks

When you run your chatbot with LangFuse enabled, you'll see:

```
📊 LangFuse Dashboard Shows:

┌─────────────────────────────────────────────────────────┐
│ Trace: User asks "Show me credit cards"                 │
│ ────────────────────────────────────────────────────    │
│ ├─ Intent Detection                      [23ms]         │
│ │  └─ LLM Call (Claude)                 [19ms]         │
│ │     Input: "Show me credit cards"                     │
│ │     Output: {domain: "conventional", vertical: ...}  │
│ │                                                       │
│ ├─ Eligibility Check Agent              [145ms]         │
│ │  ├─ Extract User Profile              [32ms]         │
│ │  ├─ Query Knowledge Base               [78ms]         │
│ │  ├─ Run Eligibility Rules              [21ms]         │
│ │  └─ Generate Response                  [14ms]         │
│ │                                                       │
│ └─ Final Response                        [168ms total]  │
│    Message: "Based on your profile..."                 │
│    Confidence: 0.92                                     │
│    Sources: [visa_gold.md, eligibility_rules.json]     │
└─────────────────────────────────────────────────────────┘

Cost Tracking:
├─ Input tokens: 1,234
├─ Output tokens: 456
└─ Total cost: $0.015
```

---

### Querying LangFuse Programmatically

```python
from langfuse_client import langfuse_client

# Get all traces for a session
traces = langfuse_client.get_traces(session_id="sess_abc123")

for trace in traces:
    print(f"Trace: {trace.name}")
    print(f"  Duration: {trace.duration}ms")
    print(f"  Status: {trace.status}")
    print(f"  Tokens: {trace.token_usage}")

# Find failed traces
failed = langfuse_client.get_traces(
    filter=f'status == "error"'
)

for trace in failed:
    print(f"Failed: {trace.name}")
    print(f"  Error: {trace.error}")
```

---

## 2. 🧪 Unit Testing with pytest

### Project Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures
├── test_models.py              # Pydantic models
├── test_intent_detection.py    # Intent classifier
├── test_eligibility.py         # Eligibility rules
├── test_knowledge.py           # JSON/Markdown loading
├── test_agents/
│   ├── test_conventional_save.py
│   ├── test_conventional_credit.py
│   ├── test_islami_save.py
│   └── test_islami_credit.py
├── test_api/
│   └── test_chat_endpoint.py
└── test_integration/
    └── test_end_to_end.py
```

---

### Setup pytest

**File:** `tests/conftest.py`

```python
import pytest
import os
import json
from pathlib import Path

# Add app to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.intent import IntentResult
from app.core.intent_detector import IntentDetector

@pytest.fixture
def intent_detector():
    """Load intent detector"""
    return IntentDetector()

@pytest.fixture
def knowledge_base():
    """Load JSON knowledge base"""
    kb_path = Path(__file__).parent.parent / "app" / "knowledge" / "structured"
    
    with open(kb_path / "conventional" / "credit_cards.json") as f:
        conventional_credit = json.load(f)
    
    with open(kb_path / "islami" / "credit_cards.json") as f:
        islami_credit = json.load(f)
    
    with open(kb_path / "conventional" / "deposit_accounts.json") as f:
        conventional_accounts = json.load(f)
    
    return {
        "conventional_credit": conventional_credit,
        "islami_credit": islami_credit,
        "conventional_accounts": conventional_accounts,
    }

@pytest.fixture
def sample_messages():
    """Common test messages"""
    return {
        "credit_card_inquiry": "Show me credit card options",
        "eligibility_check": "Can I open an account with BDT 10,000?",
        "islamic_product": "I want a Shariah-compliant product",
        "comparison": "Compare Visa Gold and Platinum",
    }
```

---

### Test Intent Detection

**File:** `tests/test_intent_detection.py`

```python
import pytest
from app.models.intent import IntentResult

class TestIntentDetection:
    """Test intent classifier accuracy"""
    
    def test_detect_credit_card_intent(self, intent_detector):
        """Should detect credit card inquiry"""
        result = intent_detector.detect("Show me credit card options")
        
        assert isinstance(result, IntentResult)
        assert result.domain == "conventional"
        assert result.vertical == "credit_card"
        assert result.intent_type == "explore"
        assert result.confidence >= 0.85
    
    def test_detect_islamic_intent(self, intent_detector):
        """Should detect Islamic banking preference"""
        result = intent_detector.detect(
            "I want a Shariah-compliant credit card"
        )
        
        assert result.domain == "islami"
        assert result.vertical == "credit_card"
        assert result.confidence >= 0.85
    
    def test_detect_eligibility_check(self, intent_detector):
        """Should detect eligibility inquiry"""
        result = intent_detector.detect(
            "Can a 16-year-old open Prime First Account?"
        )
        
        assert result.vertical == "save"
        assert result.intent_type == "eligibility"
    
    def test_low_confidence_refusal(self, intent_detector):
        """Should refuse unclear queries"""
        result = intent_detector.detect(
            "xyz abc qwerty"  # Gibberish
        )
        
        assert result.confidence < 0.5
        assert result.domain is None
```

---

### Test Models/Schemas

**File:** `tests/test_models.py`

```python
import pytest
from app.models.intent import IntentResult
from app.models.api import ChatRequest, ChatResponse

class TestChatRequest:
    """Test request validation"""
    
    def test_valid_request(self):
        """Should accept valid request"""
        req = ChatRequest(
            session_id="sess_123",
            user_message="Show me credit cards",
            channel="web",
            language="en"
        )
        assert req.session_id == "sess_123"
        assert req.channel == "web"
    
    def test_invalid_channel(self):
        """Should reject invalid channel"""
        with pytest.raises(ValueError):
            ChatRequest(
                session_id="sess_123",
                user_message="Show me credit cards",
                channel="invalid",
                language="en"
            )
    
    def test_default_language(self):
        """Should default to English"""
        req = ChatRequest(
            session_id="sess_123",
            user_message="Hello",
            channel="web"
        )
        assert req.language == "en"

class TestIntentResult:
    """Test intent model"""
    
    def test_valid_intent(self):
        """Should accept valid intent"""
        intent = IntentResult(
            domain="conventional",
            vertical="credit_card",
            intent_type="explore",
            confidence=0.92
        )
        assert intent.domain == "conventional"
        assert intent.confidence == 0.92
    
    def test_confidence_bounds(self):
        """Confidence must be 0-1"""
        with pytest.raises(ValueError):
            IntentResult(
                domain="conventional",
                confidence=1.5  # Invalid
            )
```

---

### Test Eligibility Logic

**File:** `tests/test_eligibility.py`

```python
import pytest
from app.core.eligibility import EligibilityChecker

class TestDepositAccountEligibility:
    """Test eligibility rules for deposit accounts"""
    
    @pytest.fixture
    def checker(self):
        return EligibilityChecker()
    
    def test_prime_first_age_requirement(self, checker):
        """Prime First Account requires age 13+"""
        # Eligible
        assert checker.is_eligible(
            product="prime_first_account",
            age=16,
            min_balance=1000
        ) == True
        
        # Ineligible
        assert checker.is_eligible(
            product="prime_first_account",
            age=12,
            min_balance=1000
        ) == False
    
    def test_credit_card_age_requirement(self, checker):
        """Credit cards require age 18+"""
        assert checker.is_eligible(
            product="visa_gold_credit_card",
            age=18,
            income=500000
        ) == True
        
        assert checker.is_eligible(
            product="visa_gold_credit_card",
            age=17,
            income=500000
        ) == False
    
    def test_islamic_product_eligibility(self, checker):
        """Islamic products should be accessible to all"""
        assert checker.is_eligible(
            product="visa_hasanah_platinum",
            age=25,
            income=1000000,
            religious_preference=None  # Religion not required
        ) == True
```

---

### Test Knowledge Loading

**File:** `tests/test_knowledge.py`

```python
import pytest
import json
from pathlib import Path

class TestKnowledgeBase:
    """Test JSON/Markdown knowledge loading"""
    
    def test_credit_cards_json_valid(self):
        """Credit cards JSON should be valid"""
        path = Path("app/knowledge/structured/conventional/credit_cards.json")
        
        with open(path) as f:
            data = json.load(f)
        
        assert "credit_cards_conventional" in data
        assert len(data["credit_cards_conventional"]) == 6
    
    def test_credit_card_schema(self, knowledge_base):
        """Each credit card should have required fields"""
        card = knowledge_base["conventional_credit"]["credit_cards_conventional"][0]
        
        required_fields = [
            "id", "name", "card_network", "tier", "credit_limits",
            "interest_rate", "annual_fee", "insurance"
        ]
        
        for field in required_fields:
            assert field in card, f"Missing field: {field}"
    
    def test_markdown_files_exist(self):
        """All referenced markdown files should exist"""
        products = [
            "app/knowledge/products/conventional/credit/i_need_a_credit_card/visa_gold_credit_card.md",
            "app/knowledge/products/islami/credit/i_need_a_credit_card/visa_hasanah_platinum_credit_card.md",
        ]
        
        for product_path in products:
            path = Path(product_path)
            assert path.exists(), f"Missing: {product_path}"
```

---

### Test API Endpoint

**File:** `tests/test_api/test_chat_endpoint.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

class TestChatEndpoint:
    """Test /api/chat endpoint"""
    
    def test_credit_card_query(self, client):
        """Should handle credit card inquiry"""
        response = client.post("/api/chat", json={
            "session_id": "test_sess_123",
            "user_message": "Show me credit card options",
            "channel": "web",
            "language": "en"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "domain" in data
        assert data["domain"] == "conventional"
        assert data["vertical"] == "credit_card"
        assert data["confidence"] >= 0.8
    
    def test_islamic_inquiry(self, client):
        """Should detect Islamic banking intent"""
        response = client.post("/api/chat", json={
            "session_id": "test_sess_456",
            "user_message": "I want Shariah-compliant savings",
            "channel": "web"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "islami"
    
    def test_invalid_request(self, client):
        """Should reject invalid requests"""
        response = client.post("/api/chat", json={
            "session_id": "test_123",
            "user_message": "Hello",
            # Missing 'channel'
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_session_persistence(self, client):
        """Should maintain context across messages"""
        session_id = "persistent_sess_789"
        
        # First message
        resp1 = client.post("/api/chat", json={
            "session_id": session_id,
            "user_message": "I want to open a credit card",
            "channel": "web"
        })
        assert resp1.status_code == 200
        
        # Second message (should remember context)
        resp2 = client.post("/api/chat", json={
            "session_id": session_id,
            "user_message": "Tell me about the Platinum tier",
            "channel": "web"
        })
        assert resp2.status_code == 200
        # Should reference previous context
```

---

## 3. 📊 Integration Tests

**File:** `tests/test_integration/test_end_to_end.py`

```python
import pytest
from app.main import app
from fastapi.testclient import TestClient

@pytest.mark.integration
class TestEndToEndFlow:
    """Test complete user journeys"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_credit_card_discovery_to_eligibility(self, client):
        """User discovers card and checks eligibility"""
        session_id = "e2e_test_001"
        
        # Step 1: User asks about cards
        resp1 = client.post("/api/chat", json={
            "session_id": session_id,
            "user_message": "What credit cards do you have?",
            "channel": "web"
        })
        assert resp1.status_code == 200
        assert "Visa" in resp1.json()["message"]
        
        # Step 2: User asks about specific card
        resp2 = client.post("/api/chat", json={
            "session_id": session_id,
            "user_message": "Tell me more about Visa Platinum",
            "channel": "web"
        })
        assert resp2.status_code == 200
        assert "LoungeKey" in resp2.json()["message"]
        
        # Step 3: User checks eligibility
        resp3 = client.post("/api/chat", json={
            "session_id": session_id,
            "user_message": "Am I eligible? I earn BDT 300,000/month",
            "channel": "web"
        })
        assert resp3.status_code == 200
        assert "eligible" in resp3.json()["message"].lower()
    
    def test_islamic_product_journey(self, client):
        """User explores Islamic banking"""
        session_id = "e2e_test_islamic"
        
        # Step 1: Express Islamic preference
        resp1 = client.post("/api/chat", json={
            "session_id": session_id,
            "user_message": "I need Islamic banking products",
            "channel": "web"
        })
        assert resp1.status_code == 200
        
        # Subsequent responses should stay in Islamic domain
        resp2 = client.post("/api/chat", json={
            "session_id": session_id,
            "user_message": "Show me credit cards",
            "channel": "web"
        })
        assert resp2.status_code == 200
        assert resp2.json()["domain"] == "islami"
```

---

## 4. ⚡ Load Testing

**File:** `tests/load_test.py` (using Locust)

```bash
pip install locust
```

```python
from locust import HttpUser, task, between
import json

class BankingChatbotUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    @task(3)
    def credit_card_inquiry(self):
        """Simulate user asking about credit cards"""
        self.client.post(
            "/api/chat",
            json={
                "session_id": f"load_test_{self.client.environment.stats.get()}",
                "user_message": "Show me credit card options",
                "channel": "web",
                "language": "en"
            }
        )
    
    @task(2)
    def eligibility_check(self):
        """Simulate eligibility check"""
        self.client.post(
            "/api/chat",
            json={
                "session_id": f"load_test_{self.client.environment.stats.get()}",
                "user_message": "Am I eligible for Visa Gold? I earn BDT 150,000",
                "channel": "web"
            }
        )
    
    @task(1)
    def comparison(self):
        """Simulate product comparison"""
        self.client.post(
            "/api/chat",
            json={
                "session_id": f"load_test_{self.client.environment.stats.get()}",
                "user_message": "Compare Visa Gold vs Platinum",
                "channel": "web"
            }
        )
```

**Run load test:**

```bash
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## 5. 🚀 Running Tests

### Run all tests

```bash
pytest tests/ -v
```

### Run specific test file

```bash
pytest tests/test_intent_detection.py -v
```

### Run with coverage

```bash
pytest tests/ --cov=app --cov-report=html
# Opens htmlcov/index.html for coverage report
```

### Run only unit tests (skip integration)

```bash
pytest tests/ -v -m "not integration"
```

### Run with LangFuse enabled

```bash
LANGFUSE_PUBLIC_KEY=your_key \
LANGFUSE_SECRET_KEY=your_secret \
pytest tests/ -v
```

---

## 6. 📈 CI/CD Pipeline (GitHub Actions)

**File:** `.github/workflows/test.yml`

```yaml
name: Test Banking Chatbot

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run tests
      env:
        LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
        LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
      run: |
        pytest tests/ -v --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## 7. 📋 Checklist for Production

- ✅ All unit tests pass (>85% coverage)
- ✅ All integration tests pass
- ✅ LangFuse traces show <500ms latency
- ✅ No failed intent detections (confidence >0.85)
- ✅ All eligibility rules validated
- ✅ Load test: 100 concurrent users, <2s response time
- ✅ Error handling tested (invalid inputs, missing data)
- ✅ Knowledge base validates (no missing files)

---

## Summary

| Testing Layer | Tool | Purpose |
|---------------|------|---------|
| **Observability** | LangFuse | Trace agent decisions, identify failures |
| **Unit Tests** | pytest | Test models, intent detection, eligibility |
| **Integration** | FastAPI TestClient | Test full /api/chat flow |
| **Load Testing** | Locust | Ensure 100+ concurrent users |
| **CI/CD** | GitHub Actions | Auto-run tests on every commit |


# Integration Guide: Using the 6-Graph Architecture

## Quick Start

### 1. Import the Graphs

```python
from app.core.graphs import ConversationManagerGraph
from app.models.conversation_state import ConversationState, UserProfile
```

### 2. Create Initial State

```python
state = ConversationState(
    user_message="I want a savings account",
    conversation_history=[],
    user_profile=UserProfile(),
    missing_slots=[],
    eligible_products=[],
    response=""
)
```

### 3. Invoke Root Graph

```python
manager = ConversationManagerGraph()
result = manager.invoke(state)

print(result.response)  # Get response
print(result.eligible_products)  # Get products
```

---

## Integration with FastAPI Chat Endpoint

### Current Implementation (Old)
```python
@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Old implementation using simple agents
    result = call_old_agents(request)
    return result
```

### New Implementation (6-Graph)
```python
from app.core.graphs import ConversationManagerGraph
from app.models.conversation_state import ConversationState, UserProfile

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 1. Load conversation from Redis
    redis_client = get_redis_client()
    session_id = request.session_id
    
    # Get existing state or create new
    state_dict = redis_client.hgetall(f"conversation:{session_id}")
    if state_dict:
        state = ConversationState(**state_dict)
    else:
        state = ConversationState(
            user_profile=UserProfile(),
            conversation_history=[],
            missing_slots=[],
            eligible_products=[],
            response=""
        )
    
    # 2. Update with user message
    state.user_message = request.message
    state.conversation_history.append({
        "role": "user",
        "content": request.message
    })
    
    # 3. Invoke root graph (Graph-0)
    manager = ConversationManagerGraph()
    result = manager.invoke(state)
    
    # 4. Save updated state to Redis
    redis_client.hset(
        f"conversation:{session_id}",
        mapping=result.model_dump()
    )
    
    # 5. Add to conversation history
    result.conversation_history.append({
        "role": "assistant",
        "content": result.response
    })
    
    # 6. Return response
    return {
        "response": result.response,
        "eligible_products": result.eligible_products,
        "next_action": get_next_action(result)
    }

def get_next_action(state: ConversationState) -> str:
    """Determine next action based on state"""
    if state.missing_slots:
        return "ask_for_slot"  # Graph-1 collected slots, ask for more
    elif state.intent == "eligibility":
        return "show_eligibility"  # Graph-2 determined eligibility
    elif state.intent == "compare":
        return "show_comparison"  # Graph-4 compared products
    elif state.intent == "explain":
        return "show_explanation"  # Graph-5 explained concept
    else:
        return "show_products"  # Graph-3 retrieved products
```

---

## Testing Each Graph Independently

### Test Graph-0: Conversation Manager
```python
def test_graph_0():
    from app.core.graphs import ConversationManagerGraph
    
    state = ConversationState(
        user_message="Am I eligible for a credit card?",
        conversation_history=[{"role": "user", "content": "Am I eligible for a credit card?"}],
        user_profile=UserProfile(),
        missing_slots=[],
        eligible_products=[],
        response=""
    )
    
    manager = ConversationManagerGraph()
    result = manager.invoke(state)
    
    assert result.intent == "eligibility"
    assert result.missing_slots == ["age", "income"]  # Should need these
    print("✅ Graph-0 test passed")
```

### Test Graph-1: Slot Collection
```python
def test_graph_1():
    from app.core.graphs import SlotCollectionGraph
    
    state = ConversationState(
        user_profile=UserProfile(),
        missing_slots=["age"],
        conversation_history=[{"role": "user", "content": "28"}],
        eligible_products=[],
        response=""
    )
    
    slot_graph = SlotCollectionGraph()
    result = slot_graph.invoke(state)
    
    assert result.user_profile.age == 28
    assert "age" not in result.missing_slots
    print("✅ Graph-1 test passed")
```

### Test Graph-2: Eligibility
```python
def test_graph_2():
    from app.core.graphs import EligibilityGraph
    
    profile = UserProfile(
        age=28,
        income_monthly=50000,
        employment_type="salaried"
    )
    
    state = ConversationState(
        user_profile=profile,
        banking_type="credit",
        product_category="credit",
        missing_slots=[],
        eligible_products=[],
        response=""
    )
    
    eligibility_graph = EligibilityGraph()
    result = eligibility_graph.invoke(state)
    
    assert "credit_card" in result.eligible_products or \
           "personal_loan" in result.eligible_products
    print("✅ Graph-2 test passed")
```

### Test Graph-4: Shariah Compliance
```python
def test_graph_4_shariah():
    from app.core.graphs import ComparisonGraph
    
    profile = UserProfile(
        age=30,
        religion="Muslim"
    )
    
    state = ConversationState(
        user_profile=profile,
        eligible_products=["Conventional Account", "Islamic Account"],
        comparison_mode=True,
        response=""
    )
    
    comparison_graph = ComparisonGraph()
    result = comparison_graph.invoke(state)
    
    # Should only have Shariah-compliant products
    assert "Islamic Account" in result.eligible_products
    print("✅ Graph-4 Shariah compliance test passed")
```

---

## State Persistence with Redis

### Store State
```python
def save_conversation_state(session_id: str, state: ConversationState, redis_client):
    """Save state to Redis"""
    key = f"conversation:{session_id}"
    
    # Convert state to dict
    state_dict = state.model_dump()
    
    # Store in Redis
    redis_client.hset(key, mapping=state_dict)
    
    # Set TTL to 24 hours
    redis_client.expire(key, 86400)
```

### Load State
```python
def load_conversation_state(session_id: str, redis_client) -> ConversationState:
    """Load state from Redis"""
    key = f"conversation:{session_id}"
    
    # Get from Redis
    state_dict = redis_client.hgetall(key)
    
    if not state_dict:
        # Return default state
        return ConversationState(
            user_profile=UserProfile(),
            conversation_history=[],
            missing_slots=[],
            eligible_products=[],
            response=""
        )
    
    # Convert back to ConversationState
    return ConversationState(**state_dict)
```

---

## JSON Serialization

### Configure Pydantic for JSON
```python
# In app/models/conversation_state.py

class ConversationState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # ... fields ...
    
    def json_serialize(self) -> str:
        """Serialize to JSON"""
        return self.model_dump_json()
    
    @classmethod
    def json_deserialize(cls, json_str: str) -> "ConversationState":
        """Deserialize from JSON"""
        return cls.model_validate_json(json_str)
```

### Use in Redis
```python
# Store
json_str = state.json_serialize()
redis_client.set(f"conversation:{session_id}", json_str)

# Load
json_str = redis_client.get(f"conversation:{session_id}")
state = ConversationState.json_deserialize(json_str)
```

---

## Error Handling

### Graph Invocation with Error Handling
```python
def invoke_graph_safely(graph, state: ConversationState):
    """Invoke graph with error handling"""
    try:
        result = graph.invoke(state)
        return result, None
    except ValueError as e:
        logger.error(f"Graph error: {e}")
        state.response = "I encountered an error. Please try again."
        return state, str(e)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        state.response = "Something went wrong. Please contact support."
        return state, str(e)
```

### Graceful Degradation
```python
@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        state = load_conversation_state(request.session_id, redis_client)
        state.user_message = request.message
        state.conversation_history.append({"role": "user", "content": request.message})
        
        manager = ConversationManagerGraph()
        result, error = invoke_graph_safely(manager, state)
        
        if error:
            logger.warning(f"Graph failed for {request.session_id}: {error}")
        
        save_conversation_state(request.session_id, result, redis_client)
        
        return {
            "response": result.response,
            "error": error
        }
    except Exception as e:
        logger.error(f"API error: {e}")
        return {"error": "Service unavailable"}, 500
```

---

## Monitoring & Observability

### Log Graph Execution
```python
import logging

logger = logging.getLogger(__name__)

class ConversationManagerGraph:
    def invoke(self, state: ConversationState) -> ConversationState:
        logger.info(f"Starting conversation graph for message: {state.user_message[:50]}")
        
        graph = self.build_graph()
        result = graph.invoke(state)
        
        logger.info(f"Graph completed. Intent: {result.intent}, Response length: {len(result.response)}")
        
        return result
```

### Trace with LangFuse
```python
from langfuse.callback_handler import CallbackHandler

langfuse_handler = CallbackHandler()

def invoke_with_tracing(graph, state: ConversationState):
    """Invoke graph with LangFuse tracing"""
    result = graph.invoke(
        state,
        callbacks=[langfuse_handler]
    )
    return result
```

---

## Performance Optimization

### Cache Product Data
```python
import json
from functools import lru_cache

@lru_cache(maxsize=1)
def load_products_cached():
    """Load products once and cache"""
    with open("app/data/banking_products.json", "r") as f:
        return json.load(f)

# Use in graphs:
products = load_products_cached()
```

### Batch Processing
```python
def process_multiple_conversations(requests: list[ChatRequest]):
    """Process multiple conversations in parallel"""
    from concurrent.futures import ThreadPoolExecutor
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(
            lambda req: process_single_conversation(req),
            requests
        )
    return list(results)
```

---

## Deployment Checklist

- [ ] Update `app/api/chat.py` with ConversationManagerGraph
- [ ] Update Redis state serialization
- [ ] Create test suite for all 6 graphs
- [ ] Configure logging and monitoring
- [ ] Set up LangFuse if using observability
- [ ] Load test with concurrent requests
- [ ] Deploy to staging
- [ ] Smoke test all intents (eligibility, compare, explain, explore)
- [ ] Deploy to production
- [ ] Monitor error logs
- [ ] Gather user feedback

---

## Troubleshooting

### Issue: Graph never completes (infinite loop)
**Cause:** Loop-back in Graph-1 not terminating
**Solution:** Ensure `update_state` node properly removes slot from `missing_slots`

### Issue: Missing slots never populated
**Cause:** `parse_user_answer` not extracting values correctly
**Solution:** Check regex/parsing logic for slot values

### Issue: State serialization fails
**Cause:** Non-JSON-serializable object in ConversationState
**Solution:** Ensure all fields are primitives or Pydantic models

### Issue: Intent detection always returns "explore"
**Cause:** IntentDetector not working properly
**Solution:** Check OpenAI API key and GPT-4 availability

---

## Next Steps

1. **Update Chat Endpoint** - Replace old agent code with Graph-0
2. **Add Tests** - Create test files for each graph
3. **Deploy** - Push to production with Docker
4. **Monitor** - Watch logs and user feedback
5. **Iterate** - Refine rules based on real conversations

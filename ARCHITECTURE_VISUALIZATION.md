# Architecture Visualization

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER MESSAGE                                   │
│                        "Am I eligible for X?"                               │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
          ╔═══════════════════════════════════════════════════════╗
          ║          GRAPH-0: CONVERSATION MANAGER (ROOT)         ║
          ║                   Entry Point                         ║
          ╚═══════════════════════════════════════════════════════╝
                  │
                  ├──────────────────────┬──────────────────────┤
                  │                      │                      │
           ┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐
           │ Parse        │        │ Detect       │       │ Check        │
           │ Message      │───────▶│ Intent       │──────▶│ Missing      │
           │              │        │              │       │ Slots        │
           └──────────────┘        └──────────────┘       └──────┬───────┘
                                                                 │
                ┌─────────────────────────────┬──────────────────┤
                │                             │                  │
         Missing Slots?               No Missing Slots?        
                │                             │
                ▼                             ▼
      ╔═══════════════════╗         ┌──────────────────────────────────────┐
      ║   GRAPH-1         ║         │         Route to Child Graph         │
      ║  SLOT COLLECTION  ║         │                                      │
      ║   (Loop-Back)     ║         └──────┬───────────┬────────┬──────────┘
      ║                   ║                │           │        │
      ║ 1. Identify       ║         [intent=     [intent=   [intent=
      ║    Missing Slot   ║          eligibility] compare]  explain]
      ║                   ║           │           │        │
      ║ 2. Ask Question   ║           ▼           ▼        ▼
      ║    for Slot       ║       ╔═════════╗ ╔═════════╗ ╔═════════╗
      ║                   ║       ║ GRAPH-2 ║ ║ GRAPH-4 ║ ║ GRAPH-5 ║
      ║ 3. Parse Answer   ║       ║ELIGIBLE ║ ║COMPARISO║ ║   RAG   ║
      ║                   ║       ║         ║ ║         ║ ║EXPLAININ║
      ║ 4. Update Profile ║       ║ Rules   ║ ║ Multi-  ║ ║ Grounded║
      ║                   ║       ║ Engine  ║ ║Attribute║ ║ Generatn║
      ║ 5. Loop If More   ║       ║ Filter  ║ ║Comparison║║         ║
      ║    Slots Needed   ║       ║ Shariah ║ ║Shariah  ║ ║  Docs   ║
      ║                   ║       ║         ║ ║         ║ ║         ║
      ║ [CONDITIONAL      ║       ║ Result: ║ ║ Result: ║ ║ Result: ║
      ║  LOOP-BACK]       ║       ║Products ║ ║Comparison║║ Explnatn║
      ║                   ║       ║ Found   ║ ║& Recommnd║║         ║
      ║ Result: Updated   ║       ╚═════════╝ ╚═════════╝ ╚═════════╝
      ║ user_profile +    ║           │           │        │
      ║ missing_slots=[]  ║           │           │        │
      ╚═══════════════════╝           │           │        │
                │                     │           │        │
                │                     └─────┬─────┴────┬───┘
                │                           │          │
                │                    [Default Route]
                │                           │
                │                          ▼
                │                    ╔═════════════╗
                │                    ║  GRAPH-3    ║
                │                    ║   PRODUCT   ║
                │                    ║ RETRIEVAL   ║
                │                    ║             ║
                │                    ║ 1. Search   ║
                │                    ║ 2. Fetch    ║
                │                    ║ 3. Rank     ║
                │                    ║ 4. Format   ║
                │                    ║             ║
                │                    ║ Result:     ║
                │                    ║ Products    ║
                │                    ╚═════════════╝
                │                           │
                └───────────────┬───────────┘
                                │
                                ▼
        ╔════════════════════════════════════════╗
        ║   MERGE RESULTS FROM CHILD GRAPHS      ║
        ║   Update ConversationState             ║
        ║   - eligible_products                  ║
        ║   - response                           ║
        ║   - user_profile                       ║
        ║   - missing_slots                      ║
        ╚════════════────┬────────────────────── ╝
                         │
                         ▼
        ┌─────────────────────────────────────┐
        │         FINAL RESPONSE TO USER      │
        │  (From appropriate child graph)     │
        └─────────────────────────────────────┘
```

---

## Graph-1: Slot Collection (Loop-Back Pattern)

```
                 ENTRY
                  │
                  ▼
        ┌──────────────────────┐
        │ identify_missing_slot │
        └──────────┬───────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
    missing_slots?      NO missing_slots
         │                    │
      YES│                    └────────────────────────┐
         │                                             │
         ▼                                             ▼
    ┌─────────────┐                              ┌──────────┐
    │ask_question │                              │   END    │
    └──────┬──────┘                              └──────────┘
           │
           ▼
    ┌────────────────────┐
    │parse_user_answer   │
    └──────┬─────────────┘
           │
           ▼
    ┌──────────────┐
    │update_state  │ (Remove first missing_slot)
    └──────┬───────┘
           │
           │ Loop back to identify_missing_slot
           │
           └────────────────────────────────────────────┐
                                                        │
                                    (Repeat until no missing_slots)
```

---

## Graph-2: Eligibility (Rule Engine)

```
         ENTRY
          │
          ▼
    ┌──────────────────┐
    │validate_inputs   │
    └────────┬─────────┘
             │
       ┌─────┴──────┐
       │            │
   Valid?      Invalid (missing required fields)
       │            │
      YES           └─► RETURN ERROR
       │
       ▼
    ┌────────────────┐
    │apply_rules     │ (Deterministic eligibility rules)
    │                │
    │• Salaried +    │
    │  age[18-65] +  │
    │  income ≥ 20k  │
    │                │
    │• Age ≥ 21 +    │
    │  income ≥ 30k  │
    │                │
    │• Income ≥ 50k  │
    └────────┬───────┘
             │
             ▼
    ┌──────────────────┐
    │filter_products   │ (Apply Shariah constraint if Muslim)
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────────────┐
    │store_eligible_products  │
    └────────┬────────────────┘
             │
             ▼
           END
```

---

## Graph-4: Comparison (Multi-Attribute Analysis)

```
         ENTRY
          │
          ▼
    ┌─────────────────┐
    │select_products  │ (Choose top 3)
    └────────┬────────┘
             │
       ┌─────┴──────┐
       │            │
  Have products?   NO → RETURN ERROR
       │            
      YES           
       │
       ▼
    ┌──────────────────────┐
    │normalize_attributes  │ (Convert to common units)
    │                      │
    │• min_balance → BDT   │
    │• interest_rate → %   │
    │• charges → BDT       │
    └──────┬───────────────┘
           │
           ▼
    ┌────────────────┐
    │compare_features│ (Create comparison table)
    └────────┬───────┘
             │
             ▼
    ┌────────────────────────────┐
    │apply_religious_constraints │
    │                            │
    │ IF user.religion == "Muslim":
    │   Filter by shariah_compliant=True
    └────────┬───────────────────┘
             │
             ▼
    ┌──────────────────────┐
    │generate_comparison   │ (Recommendation + rationale)
    └────────┬─────────────┘
             │
             ▼
           END
```

---

## ConversationState Data Model

```
┌────────────────────────────────────────────────────────────────────────┐
│                    CONVERSATION STATE                                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  DIALOGUE CONTROL:                                                     │
│  ├─ user_message: str                                                 │
│  ├─ intent: str (eligibility|compare|explain|explore)                │
│  ├─ banking_type: str (savings|credit)                               │
│  ├─ product_category: str (deposit|credit)                           │
│  └─ product_type: str (optional, e.g., "credit_card")               │
│                                                                        │
│  USER PROFILE:                                                         │
│  ├─ user_profile: UserProfile                                        │
│  │  ├─ age: int | None                                              │
│  │  ├─ income_monthly: float | None                                 │
│  │  ├─ income_yearly: float | None                                  │
│  │  ├─ employment_type: str (salaried|self-employed|student)       │
│  │  ├─ deposit: float | None                                        │
│  │  ├─ credit_score: int | None                                     │
│  │  ├─ religion: str (Muslim|Christian|Hindu|Buddhist|None)        │
│  │  └─ created_at: datetime                                         │
│                                                                        │
│  SLOT MANAGEMENT:                                                      │
│  └─ missing_slots: list[str]                                          │
│     (fields user hasn't provided yet)                                │
│                                                                        │
│  PRODUCT DATA:                                                         │
│  └─ eligible_products: list[str]                                      │
│     (product names matching user criteria)                           │
│                                                                        │
│  RESPONSE OUTPUT:                                                      │
│  └─ response: str                                                      │
│     (text response to send to user)                                  │
│                                                                        │
│  CONVERSATION:                                                         │
│  └─ conversation_history: list[dict]                                  │
│     [{"role": "user"/"assistant", "content": "..."}]                │
│                                                                        │
│  COMPARISON MODE:                                                      │
│  └─ comparison_mode: bool                                             │
│     (True if currently comparing products)                           │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## State Flow Through Graphs

```
Graph-0 START
│
├─ Input: ConversationState(user_message="...")
├─ Process: Parse → Detect Intent → Check Slots → Route
├─ Decision: Which child graph to invoke?
│
├─ IF missing_slots:
│  │ Invoke Graph-1
│  │ ├─ Loop: Ask → Parse → Update
│  │ └─ Return: ConversationState(missing_slots=[], user_profile={...})
│  │
│  └─ Continue to step 2
│
├─ ELIF intent == "eligibility":
│  │ Invoke Graph-2
│  │ ├─ Validate → Apply Rules → Filter → Store
│  │ └─ Return: ConversationState(eligible_products=[...])
│  │
│  └─ End
│
├─ ELIF intent == "compare":
│  │ Invoke Graph-4
│  │ ├─ Select → Normalize → Compare → Apply Shariah → Generate
│  │ └─ Return: ConversationState(response="comparison table")
│  │
│  └─ End
│
├─ ELIF intent == "explain":
│  │ Invoke Graph-5
│  │ ├─ Retrieve → Generate → Format
│  │ └─ Return: ConversationState(response="explanation")
│  │
│  └─ End
│
└─ ELSE (explore):
   │ Invoke Graph-3
   │ ├─ Build Query → Fetch → Rank → Format
   │ └─ Return: ConversationState(eligible_products=[...], response="...")
   │
   └─ End

FINAL OUTPUT
│
├─ ConversationState with:
│  ├─ response: Formatted user response
│  ├─ eligible_products: List of matching products
│  ├─ user_profile: Updated with any new information
│  └─ conversation_history: Updated with messages
│
└─ Return to API layer
```

---

## Invocation Rules

```
ALLOWED INVOCATIONS:
    ✅ Graph-0 → Graph-1
    ✅ Graph-0 → Graph-2
    ✅ Graph-0 → Graph-3
    ✅ Graph-0 → Graph-4
    ✅ Graph-0 → Graph-5

FORBIDDEN INVOCATIONS:
    ❌ Graph-1 → Any other graph
    ❌ Graph-2 → Any other graph
    ❌ Graph-3 → Any other graph
    ❌ Graph-4 → Any other graph
    ❌ Graph-5 → Any other graph
    ❌ Graph-1 ↔ Graph-2 (no circular)
    ❌ Any → Graph-0 (only entry point)

WHY?
- Prevents infinite loops
- Maintains clear hierarchy
- Ensures deterministic behavior
- Makes debugging easier
- Simplifies state management
```

---

## Intent Detection & Routing

```
User Input
    │
    ▼
IntentDetector (GPT-4)
    │
    ├─ Contains "eligible" OR "qualify"
    │  └─ intent = "eligibility" → Graph-2
    │
    ├─ Contains "compare" OR "difference"
    │  └─ intent = "compare" → Graph-4
    │
    ├─ Contains "explain" OR "how" OR "why"
    │  └─ intent = "explain" → Graph-5
    │
    └─ Default
       └─ intent = "explore" → Graph-3


Parallel: Detect Banking Type
    ├─ Contains "credit" OR "loan" OR "card"
    │  └─ banking_type = "credit" → product_category = "credit"
    │
    └─ Default
       └─ banking_type = "savings" → product_category = "deposit"
```

---

## Files & Dependencies

```
app/
├── core/
│   └── graphs/
│       ├── __init__.py                    [Imports all graphs]
│       ├── conversation_manager.py        [Graph-0 ROOT]
│       │   ├── imports:
│       │   │  ├─ StateGraph, END
│       │   │  ├─ ConversationState
│       │   │  ├─ IntentDetector
│       │   │  └─ SlotCollectionGraph, EligibilityGraph, ...
│       │   └── Key: route_and_invoke_node invokes child graphs
│       │
│       ├── slot_collection.py             [Graph-1]
│       │   ├── imports: StateGraph, END, ConversationState
│       │   └── Key: Loop-back pattern
│       │
│       ├── eligibility.py                 [Graph-2]
│       │   ├── imports: StateGraph, END, ConversationState, JSON
│       │   └── Key: Deterministic rules engine
│       │
│       ├── product_retrieval.py           [Graph-3]
│       │   ├── imports: StateGraph, END, ConversationState, JSON
│       │   └── Key: Search & ranking
│       │
│       ├── comparison.py                  [Graph-4]
│       │   ├── imports: StateGraph, END, ConversationState, JSON
│       │   └── Key: Shariah constraints
│       │
│       └── rag_explanation.py             [Graph-5]
│           ├── imports: StateGraph, END, ConversationState
│           └── Key: Grounded generation
│
└── models/
    └── conversation_state.py              [Shared State]
        ├── ConversationState
        ├── UserProfile
        └── IncomeInfo
```

---

## Performance Considerations

```
BOTTLENECK #1: Intent Detection
├─ Uses OpenAI GPT-4 API
├─ Network latency: ~1-2 seconds
└─ Mitigation: Cache results for identical queries

BOTTLENECK #2: Product Filtering
├─ JSON file loaded on each invocation
├─ File size: ~500KB (49 products)
└─ Mitigation: LRU cache at module level

BOTTLENECK #3: State Serialization
├─ Pydantic model → JSON → Redis
├─ Size: ~2-5KB per conversation
└─ Mitigation: Only serialize changed fields

OPTIMIZATION #1: Graph Compilation
├─ StateGraph.compile() called each invoke()
├─ Overhead: ~10-50ms
└─ Mitigation: Cache compiled graph in __init__

OPTIMIZATION #2: Parallel Processing
├─ Process multiple conversations simultaneously
├─ Can handle: ~10-20 concurrent requests
└─ Deployment: Use gunicorn with multiple workers

OPTIMIZATION #3: Caching Strategy
├─ Cache: Products JSON (1 hour)
├─ Cache: Compiled graphs (lifetime)
├─ Cache: Intent detection (5 minutes)
└─ Storage: Redis or in-memory dict
```

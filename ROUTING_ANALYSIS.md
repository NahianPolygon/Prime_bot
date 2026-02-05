# 🚦 Routing Logic Analysis: Product Retrieval vs Comparison

## Summary
✅ **The distinction IS clear and well-defined.** The routing logic properly distinguishes between when to invoke the comparison graph vs. product_retrieval graph. However, there's a **state management issue** in `compare_products_node` that checks for old deposit-specific slots.

---

## 1. ROUTING DECISION TREE (ConversationManager)

### Step 1: `classify_intent_node` - Determine Intent
The classifier checks conditions in this order:

```
┌─ Is comparison_status == "collecting_slots"? 
│  └─ YES → intent = "COMPARISON_QUERY" (continue comparison slot collection)
│
├─ Does message contain comparison keywords AND has matched_products?
│  ├─ Keywords: "compare", "versus", "vs", "comparison", "what's the difference", "compare these"
│  ├─ has_matched_products = bool(state.matched_products) [from previous retrieval]
│  └─ YES → intent = "COMPARISON_QUERY" (user wants to compare previously found products)
│
├─ Is product_type_in_progress set?
│  └─ YES → intent = "PRODUCT_INFO_QUERY" (continue product retrieval flow)
│
└─ Otherwise → Classify with InquiryClassifier (PRODUCT_INFO_QUERY, ELIGIBILITY_QUERY, etc.)
```

### Step 2: `route_conversation` - Route to Graph

```
Intent                          Action                          Target Graph
─────────────────────────────────────────────────────────────────────────────
COMPARISON_QUERY                Route to comparison_graph       ComparisonGraph
(continuing slot collection)    

COMPARISON_QUERY                Check has_matched_products      ComparisonGraph
(comparison keywords + results) OR has_user_mentioned_products  
                                YES → comparison_graph
                                NO  → product_retrieval (discover products)

PRODUCT_INFO_QUERY              Route to product_retrieval      ProductRetrievalGraph
(user wants products)           

ELIGIBILITY_QUERY               Route to eligibility            EligibilityGraph

GREETING                        Route to greeting               GreetingHandler

Anything else                   Route to RAG explanation        RAGExplainer
```

---

## 2. WHEN COMPARISON GRAPH IS INVOKED

### Scenario A: Direct Comparison (User Already Has Products)
```
User: "Compare Prime Fixed Deposit and Prime Kotipoti DPS"
        ↓
[classify] 
  ├─ Check: "compare" keyword detected? YES
  ├─ Check: has_matched_products? YES (from previous queries)
  └─ Intent: "COMPARISON_QUERY" 
        ↓
[route_conversation]
  ├─ Check: has_matched_products OR has_user_mentioned_products? YES
  └─ Route: "comparison" → ComparisonGraph.invoke()
```

### Scenario B: Comparison During Product Retrieval
```
User: "Show me deposits"
        ↓
[classify] → Intent: "PRODUCT_INFO_QUERY"
        ↓
[route_conversation] → "product_retrieval"
        ↓
[retrieve_products_node]
  ├─ Invokes ProductRetrievalGraph
  ├─ Returns 3 deposit products in state.matched_products
  └─ Returns response
        ↓
Bot: "I found these deposits: Prime Fixed Deposit, Prime Edu DPS, Prime Monthly Income"
        ↓
User: "Compare these three"
        ↓
[classify]
  ├─ Check: "compare" keyword detected? YES
  ├─ Check: has_matched_products? YES
  └─ Intent: "COMPARISON_QUERY"
        ↓
[route_conversation] → "comparison" → ComparisonGraph.invoke()
```

### Scenario C: Continuing Comparison Slot Collection
```
Bot (in previous turn): "Which banking type do you prefer? Conventional or Islamic?"
        ↓
User: "Conventional"
        ↓
[classify]
  ├─ Check: comparison_status == "collecting_slots"? YES
  └─ Intent: "COMPARISON_QUERY" (skip re-classification, continue)
        ↓
[route_conversation] → "comparison" → ComparisonGraph.invoke()
```

---

## 3. WHEN PRODUCT_RETRIEVAL GRAPH IS INVOKED

### Scenario A: New Product Discovery
```
User: "Show me credit cards"
        ↓
[classify] → Intent: "PRODUCT_INFO_QUERY"
        ↓
[route_conversation] → "product_retrieval" → ProductRetrievalGraph.invoke()
```

### Scenario B: Comparison Needed But No Products Yet
```
User: "Compare loans but I'm not sure which ones"
        ↓
[classify]
  ├─ Check: "compare" keyword detected? YES
  ├─ Check: has_matched_products? NO
  └─ Intent: "COMPARISON_QUERY"
        ↓
[route_conversation]
  ├─ Check: has_matched_products OR has_user_mentioned_products? NO
  └─ Route: "product_retrieval" (discover products first)
        ↓
[retrieve_products_node]
  ├─ Invokes ProductRetrievalGraph to collect user preferences (slots)
  ├─ Returns matching loan products in state.matched_products
  └─ Returns response
        ↓
Bot: "Based on your profile, I found these loans: [...]"
```

### Scenario C: Continuing Product Retrieval (Slot Collection)
```
Bot (previous turn): "What's your annual income?"
User: "1 million pesos"
        ↓
[classify]
  ├─ Check: product_type_in_progress == "deposits"? YES
  └─ Intent: "PRODUCT_INFO_QUERY" (continue deposit flow)
        ↓
[route_conversation] → "product_retrieval" → ProductRetrievalGraph.invoke()
```

---

## 4. KEY DISTINGUISHING FACTORS

### Is Comparison?
- ✅ User said "compare", "versus", "vs", "what's the difference"
- ✅ AND has previously matched products OR mentioned specific products
- ✅ OR comparison_status == "collecting_slots" (continuing)

### Is Product Retrieval?
- ✅ User asked for products: "show me", "what are", "find", "recommend"
- ✅ User is in product_type_in_progress flow (continuing slot collection)
- ✅ User wants comparison BUT no products matched yet (need to discover first)

---

## 5. CRITICAL ISSUE FOUND: State Management Bug

### Problem in `compare_products_node`

The comparison node is checking for **hardcoded deposit-specific slots**:

```python
def compare_products_node(self, state: ConversationState) -> dict:
    ...
    all_slots_collected = (
        result.get("comparison_banking_type") and           # ✅ General
        result.get("comparison_deposit_frequency") and      # ❌ DEPOSIT-ONLY
        result.get("comparison_tenure_range") and           # ❌ DEPOSIT-ONLY
        result.get("comparison_purpose")                    # ✅ General
    )
```

**This is wrong!** 

For **credit cards**, the comparison graph returns:
- `comparison_banking_type`
- `comparison_spending_pattern`
- `comparison_card_tier`
- `comparison_income`

But conversation_manager is checking for `comparison_deposit_frequency` and `comparison_tenure_range`, which don't exist for credit cards!

### Solution

The `compare_products_node` should:
1. Check what product type was detected by comparison graph
2. Check for the CORRECT slots based on that type
3. OR: Get slot names from the comparison config instead of hardcoding

**Fix:** Pass detected_product_type from comparison.py back to conversation_manager, then check appropriate slots.

---

## 6. CLEAN ROUTING FLOW (AS DESIGNED)

```
START
  ↓
[classify_intent_node]
  ├─ Checks state.comparison_status
  ├─ Checks comparison keywords + matched_products
  ├─ Checks product_type_in_progress
  ├─ Falls back to InquiryClassifier
  └─ Sets: intent, product_category, banking_type, user_profile
  ↓
[route_conversation]
  ├─ If intent == "COMPARISON_QUERY"
  │  ├─ If has_matched_products OR has_user_mentioned_products
  │  │  └─ → comparison_node
  │  └─ Else
  │     └─ → product_retrieval_node (discover first)
  │
  ├─ If intent == "PRODUCT_INFO_QUERY"
  │  └─ → product_retrieval_node
  │
  └─ Else
     └─ → other_nodes (eligibility, greeting, explanation)
  ↓
[comparison_node OR product_retrieval_node]
  ├─ Invokes respective subgraph
  ├─ Returns response
  └─ Sets state for next turn
  ↓
END
```

---

## 7. CONCLUSION

✅ **Routing logic is clear and correct** - the distinction between when to invoke comparison vs. product_retrieval is well-defined.

❌ **But there's a state management bug:**
- The `compare_products_node` checks for product-type-specific slots without knowing which product type was detected
- It should either:
  1. Receive `detected_product_type` from ComparisonGraph
  2. OR check state.comparison_status and determine slots dynamically
  3. OR rely on comparison_status flag instead of checking specific slots

**Recommendation:** Return `detected_product_type` from ComparisonGraph.invoke() result, so conversation_manager knows which slots to check.

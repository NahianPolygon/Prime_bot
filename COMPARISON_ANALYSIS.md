# Comparison Graph Analysis - Slot Extraction Flow

## 📊 Current Architecture Overview

### 1. **Product Retrieval Graph Flow** (How it Works - the BLUEPRINT)

```
User Message
    ↓
[collect_slot_node]
├─ Get MISSING SLOTS (from self.config.slots)
├─ AGGRESSIVE EXTRACTION: Try to extract ALL missing slots from current message
│  ├─ For each missing slot:
│  │  ├─ Call _extract_slot_value(slot, user_message, state)
│  │  ├─ Uses SLOT_EXTRACTION_PROMPT (LLM-based)
│  │  ├─ Updates state with extracted value
│  │  └─ Logs extracted slots
│  │
├─ Recheck remaining missing slots
│
├─ If all slots collected:
│  └─ Return: "search_products"
│
└─ If still missing slots:
   ├─ Prioritize non-banking-type slots
   ├─ Generate dynamic question for next slot
   └─ Return: ask for next slot (END and wait for user response)
```

### 2. **Slot Definition Structure** (From configs.py)

```python
@dataclass
class SlotDefinition:
    name: str                    # e.g., "age", "banking_type", "spending_pattern"
    question: str               # User-friendly question
    keywords: List[str]         # Valid options (e.g., ["male", "female"])
    extract_pattern: Optional[str]  # Regex for extraction (optional)

# Example for DEPOSITS:
SlotDefinition(
    name="age",
    question="What's your age?",
    keywords=["year", "old", "age", "50", "60"],
    extract_pattern=r"(\d{1,3})\s*(year|years|old|yo)"
)

# Example for CREDIT_CARDS:
SlotDefinition(
    name="spending_pattern",
    question="What's your spending pattern? Travel, Shopping, Business?",
    keywords=["travel", "grocery", "shopping", "business"],
    extract_pattern=r"(travel|grocery|shopping|business)"
)
```

### 3. **Slot Extraction Process** (Key Details)

```
_extract_slot_value(slot_def, user_message, state)
    ↓
Build SLOT_EXTRACTION_PROMPT with:
    - slot_name: What slot are we extracting?
    - product_type: deposits/credit_cards/loans (CONTEXT)
    - product_display_name: "Deposit Accounts", "Credit Cards", etc.
    - collected_slots: Summary of already collected slots
    - user_message: Current user input
    - current_slot: Which slot is being asked
    - valid_options: Keywords for this slot
    ↓
LLM.invoke(prompt)
    ↓
LLM analyzes message in CONTEXT of:
    - Product type (deposits vs credit cards)
    - Slot definition
    - User's answers so far
    ↓
Returns JSON with:
    - value: extracted value (or null)
    - confidence: 0.0-1.0
    - reasoning: explanation
    ↓
Parse and store in state if confidence > threshold
```

### 4. **Product Retrieval Config** (Different for each product type)

```
ProductRetrievalGraph takes a ProductGuideConfig:

DEPOSIT_ACCOUNTS_CONFIG:
    product_type: "deposits"
    slots: [age, remittance_status, account_goal, occupation, gender, 
            health_benefits_interest, locker_interest, banking_type]
    
CREDIT_CARDS_CONFIG:
    product_type: "credit_cards"
    slots: [banking_type, spending_pattern, card_tier_preference, 
            annual_income, age]
    
LOANS_CONFIG:
    product_type: "loans"
    slots: [banking_type, loan_purpose, amount_needed, repayment_period]
```

### 5. **Key Differences Between Product Types**

**DEPOSITS need:**
- Age (eligibility by age - 50+ accounts)
- Remittance status (Porijon account for NRB)
- Account goal (monthly income, lump sum, general savings)
- Occupation (teacher, student, etc.)
- Gender (women-specific benefits)
- Health benefits interest
- Locker interest

**CREDIT_CARDS need:**
- Banking type (conventional vs Islamic)
- Spending pattern (travel, shopping, business)
- Card tier preference (Gold, Platinum, World)
- Annual income (eligibility & limit)
- Age (eligibility)

**LOANS need:**
- Banking type
- Loan purpose (home, auto, personal, business)
- Amount needed
- Repayment period

---

## 🎯 How Comparison Should Work (Following Same Pattern)

### Current Comparison Problem:

```
ComparisonGraph has FIXED slots:
    slot_order = [
        "comparison_banking_type",       ← Applies to ALL products
        "comparison_deposit_frequency",  ← Only for DEPOSITS!
        "comparison_tenure_range",       ← Only for DEPOSITS!
        "comparison_purpose"              ← Vague/generic
    ]
```

### What Comparison SHOULD Do:

```
1. DETECT PRODUCT TYPE (from user message)
   ├─ "Compare JCB Gold and Visa Gold credit cards"
   │  └─ Detect: "credit_cards"
   │
   ├─ "Compare Prime Fixed Deposit and Prime Edu DPS"
   │  └─ Detect: "deposits"
   │
   └─ "Compare two loan products"
      └─ Detect: "loans"

2. SELECT PRODUCT-SPECIFIC SLOTS
   ├─ If credit_cards:
   │  ├─ comparison_banking_type
   │  ├─ comparison_spending_pattern
   │  ├─ comparison_card_tier_preference
   │  └─ comparison_income (optional)
   │
   ├─ If deposits:
   │  ├─ comparison_banking_type
   │  ├─ comparison_deposit_frequency
   │  ├─ comparison_tenure_range
   │  └─ comparison_purpose
   │
   └─ If loans:
      ├─ comparison_banking_type
      ├─ comparison_loan_purpose
      └─ comparison_amount

3. EXTRACT SLOTS (same as ProductRetrieval)
   ├─ For each missing slot:
   │  ├─ Call _extract_slot_value_llm(slot, message, state)
   │  ├─ Use LLM with CONTEXT about product type
   │  └─ Update state
   │
   └─ Ask for next missing slot if any remain

4. IDENTIFY PRODUCTS
   ├─ Extract product mentions from message
   ├─ Search RAG for mentioned products
   ├─ Match to actual products in knowledge base
   └─ Return 2-5 products to compare

5. FILTER PRODUCTS (based on collected preferences)
   └─ Use LLM to rank products against user preferences

6. GENERATE COMPARISON
   └─ Create detailed feature-by-feature comparison
```

---

## 📋 Key Learnings from Product Retrieval to Apply to Comparison

### 1. **Configuration Pattern**
```python
# Product Retrieval uses:
ProductGuideConfig(
    product_type="deposits",
    display_name="Deposit Accounts",
    slots=[...slot definitions...],
    rag_filters={"category": "deposit"},
    recommendation_prompt_template=...
)

# Comparison should similarly have:
ComparisonConfig(
    product_type="deposits",  # or credit_cards/loans
    display_name="Deposit Accounts Comparison",
    slots=[...comparison-specific slots...],
    comparison_prompt_template=...
)
```

### 2. **Slot Collection Logic**
```python
# Product Retrieval does:
1. Get missing slots from config
2. Try to extract ALL missing slots from current message
3. If none extracted, ask for NEXT missing slot
4. Repeat until all collected

# Comparison should do SAME:
1. Get missing slots for DETECTED product type
2. Extract ALL from current message
3. Ask for next slot if needed
4. Then proceed to product identification
```

### 3. **Dynamic Slot Extraction**
```python
# Uses: _extract_slot_value(slot, user_message, state)
# Prompt includes:
    - product_type (deposits vs credit_cards)
    - collected_slots (context)
    - user_message (what they said)
    - valid_options (keywords for this slot)

# Result: Smart extraction that understands context
# Example: "I prefer travel" 
#   → If credit_cards: spending_pattern = "travel"
#   → If deposits: NOT extracted (not relevant)
```

### 4. **Prioritization Logic**
```python
# Product Retrieval:
non_banking_slots = [s for s in missing if s != "banking_type"]
next_slot = non_banking_slots[0] if non_banking_slots else missing[0]

# Asks banking_type LAST to understand product intent first

# Comparison should do similar:
# Ask product-specific slots before banking_type
```

---

## 🔄 Complete Flow for Comparison (What Needs Implementation)

```
User: "Compare JCB Gold and Visa Gold credit cards"
    ↓
[classify_intent_node] → COMPARISON_QUERY ✓ (already works)
    ↓
[compare_products_node] → Invoke ComparisonGraph
    ↓
[1. DETECT_PRODUCT_TYPE]
    ├─ LLM: Extract which product category
    ├─ Keywords: "credit card" → "credit_cards"
    └─ Result: product_type = "credit_cards" ← NEEDED
    ↓
[2. SELECT_CONFIG]
    ├─ If credit_cards: Use CREDIT_CARD_COMPARISON_CONFIG
    ├─ If deposits: Use DEPOSIT_COMPARISON_CONFIG
    └─ Result: slots = [banking_type, spending_pattern, ...] ← NEEDED
    ↓
[3. EXTRACT_SLOTS]
    ├─ For each slot in config:
    │  ├─ Call _extract_slot_value_llm(slot, message, state)
    │  ├─ LLM extracts in context of product_type
    │  └─ Update state.comparison_<slot_name>
    │
    └─ Result: collected some slots, still missing others ← USES EXISTING LOGIC
    ↓
[4. ASK_FOR_NEXT_SLOT]
    └─ If slots missing: Generate question for next slot ← MODIFY
    ↓
[5. IDENTIFY_PRODUCTS]
    ├─ Extract product mentions (already works)
    ├─ Search RAG
    └─ Match products ← ALREADY WORKS
    ↓
[6. COMPARE_PRODUCTS]
    ├─ Generate personalized comparison
    └─ Return response ← ALREADY WORKS
```

---

## ✅ Implementation Checklist

**NEW to add:**
1. ✗ `_detect_comparison_product_type()` - Detect if comparing deposits/credit_cards/loans
2. ✗ Comparison configs for each product type (DEPOSIT_COMPARISON_CONFIG, etc.)
3. ✗ Slot definitions specific to comparison vs recommendation
4. ✗ Update `collect_slots_node()` to use product-type-specific slots
5. ✗ Update slot extraction to be product-type aware

**REUSE from ProductRetrieval:**
- ✓ Slot extraction LLM prompt (adapt it)
- ✓ Dynamic question generation logic
- ✓ Aggressive extraction pattern (try all slots at once)
- ✓ Missing slots logic

**ALREADY WORKING:**
- ✓ Product identification (extract mentions, search RAG)
- ✓ Comparison generation
- ✓ RAG retrieval

---

## Summary

**Key Insight:** ProductRetrieval succeeds because it:
1. Takes a CONFIG (product-specific slots)
2. Extracts slots intelligently using LLM with CONTEXT
3. Asks for missing slots one by one
4. Tracks state properly

**Comparison needs the same approach:** Instead of fixed `slot_order`, it should:
1. DETECT product type
2. Load product-type-specific comparison slots
3. Extract with context-aware LLM
4. Ask for missing slots
5. Then identify and compare products

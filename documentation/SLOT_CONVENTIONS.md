# 📋 SLOT CONVENTIONS – Entity Extraction Standard

Slots are **extracted entities** from user messages. This document defines the canonical slot names and types for the entire system.

---

## 1. Slot Naming Rules

### Rules
1. **snake_case** (not camelCase or PascalCase)
2. **Semantic** (describe the entity, not UI position)
3. **Banking-consistent** (align with banking terminology)
4. **Prefix for context** (e.g., `user_`, `product_`, `account_`)

### Examples

✅ **Good:**
- `product_name`
- `user_age`
- `account_type`
- `banking_domain`

❌ **Bad:**
- `option1` (not semantic)
- `selectedItem` (UI-based)
- `save_type` (ambiguous)
- `pname` (abbreviated)

---

## 2. Complete Slot Reference

### A. Product-Related Slots

| Slot Name | Type | Description | Example | Required By |
|-----------|------|-------------|---------|------------|
| `product_name` | string | Exact product name | "Prime First Account" | eligibility, compare |
| `product_id` | string | System product ID | "prime_first_account" | Internal |
| `product_category` | enum | Category of product | "account" / "scheme" / "credit_card" | Router |
| `product_vertical` | enum | Vertical classification | "save" / "credit_card" / "debit" | Router |
| `product_type` | enum | Specific product type | "savings_account" / "dps" / "fdr" / "visa_card" | Eligibility |

### B. Banking Domain Slots

| Slot Name | Type | Description | Example | Required By |
|-----------|------|-------------|---------|------------|
| `banking_domain` | enum | Banking type preference | "conventional" / "islami" | Router, comparator |
| `banking_preference_strength` | enum | How strong is the preference | "mandatory" / "preferred" / "flexible" | Constraint enforcer |

### C. User Profile Slots

| Slot Name | Type | Description | Example | Required By |
|-----------|------|-------------|---------|------------|
| `user_age` | int | User's age in years | 25 | Eligibility (savings, cards) |
| `user_employment_type` | enum | Employment status | "salaried" / "self_employed" / "student" / "retired" | Eligibility, onboarding |
| `user_income_monthly` | float | Monthly income in BDT | 50000 | Eligibility (credit cards), onboarding |
| `user_income_verified` | bool | Is income verified by docs | true / false | Credit card eligibility |
| `user_initial_deposit` | float | Amount to deposit in BDT | 5000 | Eligibility (savings accounts) |
| `user_credit_score` | int | Credit score (if available) | 750 | Credit card eligibility |
| `user_banking_history` | enum | Previous banking experience | "new_customer" / "existing_customer" | Onboarding |

### D. Intent Slots

| Slot Name | Type | Description | Example | Required By |
|-----------|------|-------------|---------|------------|
| `intent_type` | enum | User's primary intent | "eligibility" / "explore" / "compare" / "explain" | Router |
| `intent_confidence` | float | Confidence in detected intent | 0.92 | Fallback handler |

### E. Comparison Slots

| Slot Name | Type | Description | Example | Required By |
|-----------|------|-------------|---------|------------|
| `compare_products` | list[string] | Products to compare | ["Prime First", "Prime Youth"] | Comparison graph |
| `compare_criteria` | list[string] | Attributes to focus on | ["eligibility", "fees", "features"] | Comparison graph |
| `compare_cross_domain` | bool | Comparing conventional + islami? | true / false | Policy guard |

---

## 3. Slot Requirements by Intent

### Intent: ELIGIBILITY

**Question Example:** "Can a 16-year-old open Prime First Account?"

**Required Slots:**
- `product_name` ✓
- `user_age` ✓

**Optional Slots:**
- `user_initial_deposit`
- `user_employment_type`
- `user_income_monthly`

**Flow:**
```
1. Extract product_name and user_age
2. If missing, ask: "What's your age?" or "Which product?"
3. Check eligibility against product JSON
4. Return EligibilityResult
```

---

### Intent: EXPLORE

**Question Example:** "Show me savings accounts for 20-year-olds"

**Required Slots:**
- `product_vertical` ✓
- `banking_domain` (inferred or explicit) ✓

**Optional Slots:**
- `user_age`
- `user_employment_type`
- `user_banking_history`

**Flow:**
```
1. Extract product_vertical and banking_domain
2. Load all products matching vertical + domain
3. Filter by user_age if provided
4. Return list of eligible products
```

---

### Intent: COMPARE

**Question Example:** "Compare Prime First Account and Prime Youth Account"

**Required Slots:**
- `compare_products` (list of 2+) ✓

**Optional Slots:**
- `compare_criteria`
- `compare_cross_domain`

**Flow:**
```
1. Extract compare_products
2. Check if Islami + Conventional (violation if numeric comparison intended)
3. Load product metadata
4. Generate comparison response
```

---

### Intent: EXPLAIN

**Question Example:** "What are the benefits of Prime First Account?"

**Required Slots:**
- `product_name` ✓

**Optional Slots:**
- `explain_aspect` (feature, eligibility, fee, process)

**Flow:**
```
1. Extract product_name
2. Search markdown docs for relevant section
3. Return RAG-based explanation
```

---

## 4. Extraction Rules (for LLM Prompt)

### Extract Product Name

```
USER: "Can I open the Prime First one?"
→ product_name = "Prime First Account"

USER: "What about the youth account?"
→ product_name = "Prime Youth Account"

USER: "Show me DPS products"
→ product_type = "dps"  (not product_name)
```

### Extract Age

```
USER: "I'm 16 years old"
→ user_age = 16

USER: "I'm in college"
→ user_age = null, user_employment_type = "student"

USER: "I just turned 18"
→ user_age = 18
```

### Extract Banking Domain

```
USER: "Islamic banking options"
→ banking_domain = "islami"

USER: "Regular account"
→ banking_domain = "conventional"

USER: "What's the difference between Islami and regular?"
→ banking_domain = null (implicit in both)
```

### Extract Employment

```
USER: "I'm a salaried employee"
→ user_employment_type = "salaried"

USER: "I'm a freelancer"
→ user_employment_type = "self_employed"

USER: "I'm in college"
→ user_employment_type = "student"

USER: "I'm retired"
→ user_employment_type = "retired"
```

---

## 5. Slot Extraction LLM Prompt Template

```
You are extracting banking-related entities from user messages.

Extract ONLY these slots:
- product_name (string): Exact product name
- product_type (enum): "savings_account" | "dps" | "fdr" | "visa_card" | "mastercard"
- product_vertical (enum): "save" | "credit_card" | "debit"
- banking_domain (enum): "conventional" | "islami"
- user_age (int): Age in years
- user_income_monthly (float): Monthly income in BDT
- user_employment_type (enum): "salaried" | "self_employed" | "student" | "retired"
- user_initial_deposit (float): Initial deposit amount in BDT
- intent_type (enum): "eligibility" | "explore" | "compare" | "explain"

Return JSON. If slot is not mentioned, omit it (don't use null).

USER MESSAGE: "Can a 20-year-old student with 5,000 taka open Prime First Account?"

RESPONSE:
{
  "product_name": "Prime First Account",
  "user_age": 20,
  "user_employment_type": "student",
  "user_initial_deposit": 5000,
  "intent_type": "eligibility"
}
```

---

## 6. Slot Validation Rules

### Validation Table

| Slot | Type | Min | Max | Regex |
|------|------|-----|-----|-------|
| `user_age` | int | 10 | 120 | - |
| `user_income_monthly` | float | 0 | 1000000 | - |
| `user_initial_deposit` | float | 0 | 10000000 | - |
| `user_credit_score` | int | 300 | 900 | - |
| `product_name` | string | 5 | 100 | `^[A-Za-z0-9\s]+$` |
| `banking_domain` | enum | - | - | Must be in: ["conventional", "islami"] |
| `user_employment_type` | enum | - | - | Must be in: ["salaried", "self_employed", "student", "retired"] |

### Validation Code

```python
from pydantic import BaseModel, field_validator

class ExtractedSlots(BaseModel):
    product_name: Optional[str] = None
    user_age: Optional[int] = None
    user_income_monthly: Optional[float] = None
    user_employment_type: Optional[str] = None
    
    @field_validator('user_age')
    def validate_age(cls, v):
        if v is not None and not (10 <= v <= 120):
            raise ValueError('Age must be between 10 and 120')
        return v
    
    @field_validator('user_income_monthly')
    def validate_income(cls, v):
        if v is not None and not (0 <= v <= 1000000):
            raise ValueError('Income must be between 0 and 1,000,000 BDT')
        return v
```

---

## 7. Missing Slot Handling

If required slots are missing:

```python
def get_missing_slots(extracted: dict, intent_type: str) -> list[str]:
    """Return list of missing required slots"""
    
    required_by_intent = {
        "eligibility": ["product_name", "user_age"],
        "explore": ["product_vertical"],
        "compare": ["compare_products"],
        "explain": ["product_name"]
    }
    
    required = required_by_intent[intent_type]
    return [slot for slot in required if slot not in extracted]

# Usage
missing = get_missing_slots(
    {"product_name": "Prime First"},
    "eligibility"
)
# Returns: ["user_age"]
```

---

## 8. Slot vs Conversation State

### Slots (Ephemeral)
- Extracted from current message
- Used to invoke graphs
- Thrown away after processing

### Conversation State (Persistent)
- Accumulated over conversation
- Stored in Redis/memory
- Used for follow-up context

### Example Flow

```
Turn 1:
  USER: "Can I open Prime First?"
  EXTRACTED SLOTS: {product_name: "Prime First"}
  MISSING SLOTS: ["user_age"]
  → Ask: "How old are you?"
  → STATE: {product_name: "Prime First", missing_slots: ["user_age"]}

Turn 2:
  USER: "I'm 20"
  EXTRACTED SLOTS: {user_age: 20}
  MERGED STATE: {product_name: "Prime First", user_age: 20}
  → Run eligibility check
  → STATE: {product_name: "Prime First", user_age: 20, is_eligible: true}
```

---

## 9. Testing Slot Extraction

```python
# tests/test_slot_extraction.py

def test_extract_eligibility_query():
    msg = "Can a 16-year-old with 5000 taka open Prime First?"
    slots = extract_slots(msg)
    
    assert slots['product_name'] == "Prime First Account"
    assert slots['user_age'] == 16
    assert slots['user_initial_deposit'] == 5000

def test_extract_explore_query():
    msg = "Show me Islamic savings accounts"
    slots = extract_slots(msg)
    
    assert slots['banking_domain'] == "islami"
    assert slots['product_vertical'] == "save"

def test_validation_fails_on_invalid_age():
    from app.models.intent import ExtractedSlots
    
    with pytest.raises(ValueError):
        ExtractedSlots(user_age=150)  # Out of range
```


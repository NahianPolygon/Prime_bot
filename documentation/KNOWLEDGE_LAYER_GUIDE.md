# Knowledge Layer Guide: JSON + Markdown Strategy

## Problem Statement
You currently have all information in MD files. But how can JSON and MD files work together?

**Answer:** They serve different purposes in the chatbot workflow:

---

## Layer Architecture

### 🤖 LAYER 1: JSON (System/Bot Uses)
**Purpose:** Machine-readable metadata for the bot to filter, compare, and apply rules

**What goes in JSON:**
- Product attributes (min_balance, min_age, features, constraints)
- Eligibility criteria (conditions the system checks)
- Product IDs and references
- Rules in machine-readable format

**Used by:** Eligibility Graph, Comparison Graph, Product Retrieval

---

### 📖 LAYER 2: Markdown (Customer/RAG Uses)
**Purpose:** Human-readable documentation for customers and RAG explanations

**What goes in MD:**
- Product descriptions
- Benefits and features (in human language)
- FAQs about the product
- How to apply
- Example scenarios
- Regulatory information

**Used by:** RAG system (for explaining why product is good), Customer education

---

## Real Example: Prime First Account

### ❌ WRONG WAY (All info in Markdown)
```markdown
# Prime First Account

This is our flagship account for young professionals. 
Minimum balance is 1000. You must be at least 13 years old.
No income required. Free for the first 3 years then 500 taka annual fee.
Monthly statement, ATM access included.
```

**Problems:**
- Bot cannot programmatically check "min balance = 1000"
- Bot cannot programmatically check "age >= 13"
- Bot cannot filter: "which accounts can 15-year-old open?"
- Bot must use LLM to parse the MD text (slow, unreliable)

---

### ✅ RIGHT WAY (JSON for system + Markdown for customer)

#### Step 1: Store SYSTEM DATA in JSON

**File:** `app/knowledge/structured/conventional/deposit_accounts.json`
```json
{
  "prime_first_account": {
    "product_id": "prime_first_account",
    "product_name": "Prime First Account",
    "category": "deposit_account",
    "banking_type": "conventional",
    
    "eligibility": {
      "min_age": 13,
      "max_age": null,
      "min_income": null,
      "min_deposit": 1000,
      "employment_types": ["any"],
      "credit_score_required": false
    },
    
    "attributes": {
      "monthly_fee": 0,
      "annual_fee": 500,
      "free_period_months": 36,
      "atm_access": true,
      "cheque_book": false,
      "statement_frequency": "monthly"
    },
    
    "markdown_ref": "knowledge/products/conventional/save/deposit_accounts/prime_first_account.md"
  }
}
```

#### Step 2: Store CUSTOMER INFO in Markdown

**File:** `app/knowledge/products/conventional/save/deposit_accounts/prime_first_account.md`
```markdown
# Prime First Account

## Overview
Our flagship account designed for young professionals and students starting their banking journey.

## Who Can Open?
- Minimum age: 13 years
- No income requirement
- Available to all employment types (employed, self-employed, unemployed, student)

## What You Get
✅ Free ATM access nationwide
✅ Free monthly statement
✅ Multi-currency support
✅ Digital banking access

## Fees
- First 3 years: FREE
- After 3 years: ৳500 annual fee
- No monthly fees

## Minimum Balance
- ৳1,000 to open
- No maintenance balance required

## How to Apply?
1. Visit nearest branch with valid ID
2. Fill form [link to form PDF]
3. Provide proof of age
4. Get approval in 24 hours

## FAQs

**Q: Can a 12-year-old open this account?**
A: No, minimum age is 13. Consider our Prime Student account (min age 10).

**Q: What if I can't maintain 1000 balance?**
A: You won't be able to open this account. Try Prime Lite (min balance ৳500).

**Q: Do I need to show income proof?**
A: No, income is not required for this account.

## Example Scenarios

### Scenario 1: 15-year-old student
✅ **ELIGIBLE** - Meets age requirement, no income needed

### Scenario 2: 25-year-old with 50,000 monthly income
✅ **ELIGIBLE** - Meets all criteria

### Scenario 3: 35-year-old with only 500 taka to deposit
❌ **NOT ELIGIBLE** - Minimum balance is 1,000
💡 **Suggestion:** Prime Lite Account requires only ৳500

## Related Products
- Prime Lite Account (lower balance)
- Prime Student Account (for younger age group)
- Prime Salary Account (with employer verification)

## Regulatory Information
This account is FDIC insured up to maximum limit per Bangladesh Bank guidelines.
```

---

## System Workflow Example

### User Query: "Can a 16-year-old with 5,000 taka open Prime First Account?"

#### Step 1: System Uses JSON for Eligibility Check
```python
# eligibility_graph.py
state = {
  "user_profile": {
    "age": 16,
    "deposit": 5000
  },
  "product_name": "prime_first_account"
}

# Load JSON
product = load_json("conventional/deposit_accounts.json")["prime_first_account"]

# Check eligibility against JSON
eligible = (
  state["user_profile"]["age"] >= product["eligibility"]["min_age"]  # 16 >= 13 ✓
  and state["user_profile"]["deposit"] >= product["eligibility"]["min_deposit"]  # 5000 >= 1000 ✓
)
# Result: eligible = True
```

#### Step 2: System Uses Markdown for Explanation
```python
# comparison_graph.py or RAG system
if eligible:
  # Fetch markdown for detailed explanation
  md_content = load_markdown("knowledge/products/conventional/save/deposit_accounts/prime_first_account.md")
  
  # Extract benefits for customer
  response = f"""
  ✅ You are ELIGIBLE for Prime First Account!
  
  Here's what you get:
  {extract_benefits_from_markdown(md_content)}
  
  How to apply:
  {extract_how_to_apply_from_markdown(md_content)}
  """
```

#### Step 3: User Gets Human-Friendly Explanation
```
✅ You are ELIGIBLE for Prime First Account!

Here's what you get:
✅ Free ATM access nationwide
✅ Free monthly statement
✅ Multi-currency support
✅ Digital banking access

For the first 3 years: COMPLETELY FREE
After 3 years: ৳500 annual fee

How to apply?
1. Visit nearest branch with valid ID
2. Fill form [link to form PDF]
3. Provide proof of age
4. Get approval in 24 hours

[Read full product details]
```

---

## Eligibility Rules Storage

### ❌ WRONG: Store rules in Markdown
```markdown
# Eligibility Rules

Prime First Account is eligible for:
- Age >= 13
- Deposit >= 1000
...
```
**Problem:** Bot cannot read and execute these rules

---

### ✅ RIGHT: Store rules in JSON, reference in Markdown

**File:** `app/knowledge/structured/conventional/deposit_accounts.json`
```json
{
  "prime_first_account": {
    "eligibility": {
      "min_age": 13,
      "max_age": null,
      "min_income": null,
      "min_deposit": 1000,
      "employment_types": ["any"],
      "credit_score_required": false
    }
  }
}
```

**File:** `app/knowledge/products/conventional/save/deposit_accounts/prime_first_account.md`
```markdown
## Who Can Open?
- Minimum age: 13 years
- No income requirement
- Available to all employment types
- Minimum balance: ৳1,000
```

**How system uses both:**
1. JSON for filtering (fast, programmatic)
2. Markdown for explanation (human-friendly, RAG-ready)

---

## Complete File Structure

```
app/knowledge/
├── structured/  (SYSTEM DATA - JSON)
│   ├── conventional/
│   │   ├── deposit_accounts.json  ← All account metadata & eligibility rules
│   │   ├── deposit_schemes.json   ← All scheme metadata & eligibility rules
│   │   └── credit_cards.json      ← All card metadata & eligibility rules
│   └── islami/
│       ├── deposit_accounts.json
│       ├── deposit_schemes.json
│       └── credit_cards.json
│
├── products/  (CUSTOMER INFO - Markdown)
│   ├── conventional/
│   │   ├── save/
│   │   │   ├── deposit_accounts/
│   │   │   │   ├── prime_first_account.md      ← Customer explanation
│   │   │   │   ├── prime_plus_account.md
│   │   │   │   └── prime_lite_account.md
│   │   │   └── deposit_schemes/
│   │   │       ├── regular_dps.md
│   │   │       ├── smart_dps.md
│   │   │       └── flexible_fdr.md
│   │   └── credit/
│   │       ├── visa_gold.md
│   │       ├── visa_platinum.md
│   │       └── mastercard_world.md
│   └── islami/
│       └── save/
│           ├── deposit_accounts/
│           │   ├── mudaraba_account.md
│           │   └── wakala_account.md
│           └── deposit_schemes/
│               ├── mudaraba_dps.md
│               └── mudaraba_fdr.md
│
└── unstructured/  (RAG DOCUMENTS - Pdfs/Docs)
    ├── brochures/
    │   ├── prime_first_account_brochure.pdf
    │   └── ...
    ├── policies/
    │   ├── privacy_policy.pdf
    │   └── terms_and_conditions.pdf
    └── faqs/
        ├── general_banking_faq.pdf
        └── islamic_banking_faq.pdf
```

---

## Data Flow Diagram

```
USER QUERY
    ↓
[INTENT DETECTOR - NLP]
    ↓
[GRAPH-0 ROUTER]
    ↓
    ├─→ "explore" intent → [GRAPH-1: SLOT COLLECTION]
    │                              ↓
    │                        [Ask for banking_type, product_category]
    │                              ↓
    │
    ├─→ "eligibility" intent → [GRAPH-2: ELIGIBILITY]
    │                              ↓
    │                      [LOAD JSON for rules]
    │                        Check eligibility
    │                              ↓
    │                      [IF ELIGIBLE: Load Markdown]
    │                        Fetch benefits & how to apply
    │                              ↓
    │
    └─→ "explain" intent → [GRAPH-3: RAG]
                               ↓
                        [LOAD Markdown files]
                        [LOAD unstructured docs]
                        [Chunk & embed]
                        [Retrieve relevant sections]
                               ↓
RESPONSE TO USER (Human-friendly explanation)
```

---

## Summary: Why Both JSON and Markdown?

| Aspect | JSON | Markdown |
|--------|------|----------|
| **Purpose** | System filtering & rules | Customer explanation & RAG |
| **Format** | Machine-readable | Human-readable |
| **Who uses** | Bot algorithms | LLM + Customers |
| **Example data** | `min_age: 13` | "Minimum age: 13 years old" |
| **Speed** | Fast (direct comparison) | Slower (RAG retrieval) |
| **Maintainability** | Easy to update rules | Easy to explain changes |
| **Example use** | "Filter accounts for age 16" | "Explain why this product is good" |

---

## Implementation Steps

### Phase 1: Create JSON Structure
1. Map all product attributes to JSON fields
2. Define eligibility rules in JSON format
3. Create JSON file for each product type

### Phase 2: Create Markdown Documentation
1. Write detailed explanations for each product
2. Include FAQs and examples
3. Add how-to-apply instructions

### Phase 3: Link JSON to Markdown
1. Add `markdown_ref` field in JSON pointing to MD file
2. Implement loader to fetch both JSON + Markdown
3. Test eligibility → explanation flow

### Phase 4: Implement RAG Layer
1. Chunk Markdown files
2. Create embeddings
3. Implement retriever for "explain" intent

---

## Next Steps

**Questions for you:**

1. **For each product**, what attributes should go in JSON?
   - Example: For Prime First Account: min_age, min_deposit, annual_fee, atm_access?

2. **For eligibility rules**, should they be:
   - Option A: Simple comparisons? (age >= 13 AND deposit >= 1000)
   - Option B: Complex conditions? (age >= 13 AND (income >= 50000 OR student))
   - Option C: Rules engine? (External rules file with conditions)

3. **Current MD files**, can you share:
   - One example product MD file?
   - One example eligibility rule you have?

Then I can help you:
- Create exact JSON schema for your products
- Show how to migrate existing MD content to JSON + Markdown layers
- Write the Python code to load and use both files


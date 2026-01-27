# 🏦 Bank Chatbot – Product Classification & Conversational Architecture

This document provides **full technical documentation** for the banking chatbot system discussed throughout the conversation. It covers **architecture, intent understanding, product classification, domain separation (Conventional vs Islami), knowledge storage, graph-based reasoning, and shared conversation state**.

The system is designed to be **production-grade, explainable, extensible**, and compatible with **FastAPI + multi-agent orchestration**.

---

## 1. 🎯 Project Objective

The goal of this project is to build an **intelligent banking chatbot** that can:

* Understand **user intent** from free-form natural language
* Distinguish between **Conventional** and **Islami (Shariah-compliant)** banking
* Correctly classify **product domain, category, type, and name**
* Route the query to the **correct domain-specific agent**
* Answer questions using **structured knowledge + RAG**
* Maintain **conversation memory across turns and agents**

This is **not just a chatbot**, but a **banking decision engine**.

---

## 2. 🧠 Core Concepts

### 2.1 Product Classification Schema

Every user query is normalized into the following schema:

```json
{
  "banking_type": "islami" | "conventional" | null,
  "product_category": "account" | "scheme" | "credit" | null,
  "product_type": "string" | null,
  "product_name": "string" | null
}
```

This schema is the **backbone** of routing, reasoning, and response generation.

---

## 3. 🗂 Folder Structure (Final)

```
bank-chatbot/
│
├── app/
│   ├── main.py                 # FastAPI entry
│   ├── api/
│   │   └── chat.py             # /chat endpoint
│   │
│   ├── core/
│   │   ├── conversation.py     # Global conversation state (Redis)
│   │   ├── intent_detector.py  # Banking type, product, feature detection
│   │   ├── router.py           # Agent routing logic
│   │
│   ├── domains/
│   │   ├── conventional/
│   │   │   ├── save/
│   │   │   │   ├── agent.py
│   │   │   │   ├── deposit_accounts.py
│   │   │   │   └── deposit_schemes.py
│   │   │   └── credit/
│   │   │       ├── visa/
│   │   │       │   ├── gold.json
│   │   │       │   └── platinum.json
│   │   │       ├── mastercard/
│   │   │       │   ├── gold.json
│   │   │       │   ├── platinum.json
│   │   │       │   └── world.json
│   │   │       └── jcb/
│   │   │           ├── gold.json
│   │   │           └── platinum.json
│   │   │
│   │   └── islami/
│   │       ├── save/
│   │       │   ├── agent.py
│   │       │   ├── deposit_accounts.py
│   │       │   └── deposit_schemes.py
│   │       └── credit/
│   │           └── visa/
│   │               ├── hasanah_gold.json
│   │               └── hasanah_platinum.json
│   │
│   ├── knowledge/
│   │   ├── structured/                     # Machine-readable (NO LLM creativity)
│   │   │   ├── conventional/
│   │   │   │   ├── deposit_accounts.json
│   │   │   │   ├── deposit_schemes.json
│   │   │   │   └── credit_cards.json
│   │   │   │
│   │   │   └── islami/
│   │   │       ├── deposit_accounts.json
│   │   │       ├── deposit_schemes.json
│   │   │       └── credit_cards.json
│   │   │
│   │   ├── products/                       # 👈 Individual product documentation
│   │   │   ├── conventional/
│   │   │   │   ├── save/
│   │   │   │   │   ├── deposit_accounts/
│   │   │   │   │   │   ├── prime_first_account.md
│   │   │   │   │   │   ├── prime_youth_account.md
│   │   │   │   │   │   └── prime_savings_account.md
│   │   │   │   │   │
│   │   │   │   │   └── deposit_schemes/
│   │   │   │   │       ├── prime_kotipoti_dps.md
│   │   │   │   │       └── prime_fixed_deposit.md
│   │   │   │   │
│   │   │   │   └── credit_card/
│   │   │   │       ├── platinum_credit_card.md
│   │   │   │       └── gold_credit_card.md
│   │   │   │
│   │   │   └── islami/
│   │   │       ├── save/
│   │   │       │   ├── deposit_accounts/
│   │   │       │   │   ├── prime_hasanah_first_account.md
│   │   │       │   │   └── prime_hasanah_youth_account.md
│   │   │       │   │
│   │   │       │   └── deposit_schemes/
│   │   │       │       ├── mudaraba_dps.md
│   │   │       │       └── monthly_income_scheme.md
│   │   │       │
│   │   │       └── credit_card/
│   │   │           └── islami_credit_card.md
│   │   │
│   │   └── unstructured/                   # Large docs, PDFs, policies
│   │       ├── brochures/
│   │       ├── policies/
│   │       └── faqs/
│   │
│   ├── rag/
│   │   ├── indexer.py
│   │   ├── retriever.py
│   │   └── prompt_templates.py
│   │
│   ├── graphs/
│   │   ├── eligibility_graph.py
│   │   ├── comparison_graph.py
│   │   └── onboarding_graph.py
│   │
│   └── models/
│       ├── context.py
│       ├── product.py
│       └── response.py
│
├── requirements.txt
└── README.md
```

---

## 4. 🔁 Global Shared State (Conversation Memory)

### Purpose

Conversation state allows **multiple agents** to cooperate without losing context.

### Storage

* Redis (keyed by `session_id`)

### Complete ConversationState Schema

```python
ConversationState = {
    # routing & intent
    "intent": str,  # explore | eligibility | compare | explain

    # product classification
    "banking_type": "islami" | "conventional" | None,
    "product_category": "account" | "scheme" | "credit" | None,
    "product_type": str | None,        # savings | deposit | credit_card
    "product_name": str | None,        # Visa Platinum, Hasanah Gold

    # user profile
    "user_profile": {
        "age": int | None,
        "religion": "islami" | "conventional" | None,
        "employment_type": "salaried" | "self_employed" | "student" | "retired" | None,
        "income": {
            "amount": float | None,        # Monthly income in BDT
            "frequency": "monthly" | "yearly" | None,
            "verified": bool              # From salary slip / tax cert
        },
        "deposit": float | None,          # Initial deposit amount
        "credit_score": int | None        # For credit cards (optional)
    },

    # dialogue control
    "missing_slots": list[str],
    "eligible_products": list[dict],
    "comparison_mode": bool,
    "last_agent": str,
    "response": str
}
```

### Field Definitions

| Field | Type | Purpose |
|-------|------|---------|
| `intent` | str | Current user intent: explore, eligibility, compare, explain |
| `banking_type` | str | Islami or Conventional banking preference |
| `product_category` | str | Account, Scheme, or Credit products |
| `product_type` | str | Specific product type (savings, deposit, credit_card) |
| `product_name` | str | Exact product name (e.g., "Visa Platinum", "Hasanah Gold") |
| `user_profile.age` | int | User's age for eligibility |
| `user_profile.religion` | str | Religious preference affecting product eligibility |
| `user_profile.employment_type` | str | salaried, self_employed, student, or retired |
| `user_profile.income.amount` | float | Monthly income in BDT |
| `user_profile.income.frequency` | str | monthly or yearly |
| `user_profile.income.verified` | bool | Verified via salary slip or tax certificate |
| `user_profile.deposit` | float | Initial deposit amount in BDT |
| `user_profile.credit_score` | int | Credit score for card eligibility (optional) |
| `missing_slots` | list | Remaining required fields to collect |
| `eligible_products` | list | Products that match user's eligibility |
| `comparison_mode` | bool | Whether user is comparing multiple products |
| `last_agent` | str | Last graph/agent that processed the state |
| `response` | str | Final response to send to user |

All agents **read and write** to this shared state.

---

## 5. 🧭 Intent Detection & Routing

### intent_detector.py

Responsibilities:

* Detect **banking type** using keywords:

  * Islami → mudaraba, shariah, halal, profit-sharing
  * Conventional → interest, fixed rate, APR

* Detect **product category**:

  * account → savings, current, student
  * scheme → DPS, FDR, monthly deposit
  * credit → credit card, visa, mastercard, jcb

* Detect **product intent**:

  * eligibility → "Can I open?"
  * explore → "Show me products"
  * compare → "Compare products"
  * explain → "Why?" or "How?"

### router.py

Routes the request to:

```
(conventional | islami)
   └── (save | credit)
         └── domain agent
```

**Note:** Debit is a future feature. Investment products are out of scope for phase 1.

---

## 6. 🧠 Knowledge Storage Design

### 6.1 Structured Knowledge (JSON)

**Purpose:** Machine-readable product metadata for system logic (eligibility, filtering, comparison)

Each JSON file contains **product attributes** (NOT human-readable descriptions).

#### Structure

**conventional/deposit_accounts.json**
```json
{
  "prime_first_account": {
    "product_id": "prime_first_account",
    "product_name": "Prime First Account",
    "category": "savings",
    "type": "account",
    "min_balance": 1000,
    "min_age": 13,
    "max_age": null,
    "income_required": false,
    "employment_types": null,
    "features": ["low_minimum", "student_eligible"],
    "documents_required": ["nid", "address_proof"],
    "profit_model": null,
    "markdown_ref": "knowledge/products/conventional/save/deposit_accounts/prime_first_account.md"
  },
  "prime_youth_account": { ... },
  "prime_savings_account": { ... }
}
```

**conventional/deposit_schemes.json**
```json
{
  "prime_kotipoti_dps": {
    "product_id": "prime_kotipoti_dps",
    "product_name": "Prime Kotipoti DPS",
    "category": "scheme",
    "type": "deposit",
    "min_balance": 10000,
    "min_age": 18,
    "min_income_monthly": 15000,
    "min_deposit": 10000,
    "duration_months": [6, 12, 24, 36, 60],
    "features": ["regular_savings", "fixed_returns"],
    "markdown_ref": "knowledge/products/conventional/save/deposit_schemes/prime_kotipoti_dps.md"
  },
  "prime_fixed_deposit": { ... }
}
```

**conventional/credit_cards.json**
```json
{
  "prime_platinum": {
    "product_id": "prime_platinum",
    "product_name": "Prime Platinum Credit Card",
    "type": "credit_card",
    "network": "visa",
    "min_age": 21,
    "max_age": 65,
    "min_income_monthly": 50000,
    "min_credit_score": 700,
    "employment_required": ["salaried", "self_employed"],
    "features": ["reward_points", "lounge_access"],
    "markdown_ref": "knowledge/products/conventional/credit/visa/platinum.md"
  }
}
```

### Usage Pattern

1. **Load** all products from JSON at startup
2. **Filter** by attributes (age, income, employment, etc.)
3. **Apply eligibility rules** against JSON metadata
4. **Fetch markdown** from `markdown_ref` for customer-friendly details

### 6.2 Product Documentation (Markdown)

**Purpose:** Human-readable product information for customers (RAG retrieval)

Each markdown file contains:
- Detailed product description
- Benefits & features (customer language)
- Application process
- FAQs
- Profit/interest rates
- Terms & conditions

Located at: `knowledge/products/{banking_type}/{feature}/{section}/{product_name}.md`

Example files:
- `knowledge/products/conventional/save/deposit_accounts/prime_first_account.md`
- `knowledge/products/conventional/save/deposit_schemes/prime_kotipoti_dps.md`
- `knowledge/products/conventional/credit/visa/platinum_credit_card.md`
- `knowledge/products/islami/save/deposit_accounts/prime_hasanah_first_account.md`

### 6.3 Unstructured Knowledge (RAG)

**Purpose:** Additional policy documents, FAQs, regulatory info

Used by RAG layer when answering "WHY?" questions about:
- Shariah compliance rules
- Interest vs profit-sharing concepts
- Banking regulations
- Product policies

---

### 6.4 Eligibility Rules Engine

**Purpose:** Deterministic rules for product qualification

### Savings Accounts (Conventional)

| Rule | Requirement |
|------|-------------|
| **Minimum Age** | 18+ |
| **Maximum Age** | No limit |
| **Income** | Optional |
| **Minimum Deposit** | 1,000 BDT |
| **Employment** | Any (students eligible) |
| **Documents** | NID + Address Proof |
| **Religion** | N/A |

**Special Cases:**
- Age 13-17: Student account variant
- Age 65+: Senior account with benefits

### Savings Accounts (Islami)

| Rule | Requirement |
|------|-------------|
| **Minimum Age** | 18+ |
| **Maximum Age** | No limit |
| **Income** | Optional |
| **Minimum Deposit** | 2,000 BDT |
| **Employment** | Any (students eligible) |
| **Documents** | NID + Address Proof |
| **Religion** | Islamic belief (optional flag) |
| **Shariah Check** | Must not have interest-bearing debts |

### Deposit Schemes (Conventional DPS/FDR)

| Rule | Requirement |
|------|-------------|
| **Minimum Age** | 18+ |
| **Income Required** | Monthly: 15,000+ BDT |
| **Minimum Deposit** | 10,000 BDT |
| **Deposit Duration** | 6 months - 5 years |
| **Documents** | NID + Tax Certificate (for 500k+) |

**Eligibility Logic:**
```
IF age >= 18 AND monthly_income >= 15000 AND initial_deposit >= 10000
  THEN eligible = True
ELSE eligible = False
```

### Deposit Schemes (Islami Mudaraba)

| Rule | Requirement |
|------|-------------|
| **Minimum Age** | 18+ |
| **Income Required** | Monthly: 20,000+ BDT |
| **Minimum Deposit** | 15,000 BDT |
| **Deposit Duration** | 6 months - 5 years |
| **Documents** | NID + Tax Certificate (for 750k+) |
| **Shariah Compliance** | Profit-sharing only, no interest |

### Credit Cards (Conventional)

| Rule | Requirement |
|------|-------------|
| **Minimum Age** | 21+ |
| **Maximum Age** | 65+ (limited) |
| **Monthly Income** | 30,000+ BDT (Gold), 50,000+ (Platinum) |
| **Employment Type** | Salaried / Self-employed |
| **Credit Score** | Good (>650) |
| **Documents** | NID + Salary Slip (3 months) + Tax Certificate |

**Card Tiers:**
```
IF monthly_income >= 30,000 AND age >= 21 AND employment == "salaried"
  THEN eligible_for = ["Gold"]
  
IF monthly_income >= 50,000 AND age >= 25 AND employment_stable == True
  THEN eligible_for = ["Gold", "Platinum"]
  
IF monthly_income >= 100,000 AND age >= 30 AND credit_score >= 700
  THEN eligible_for = ["Gold", "Platinum", "World"]
```

### Credit Cards (Islami)

| Rule | Requirement |
|------|-------------|
| **Minimum Age** | 21+ |
| **Maximum Age** | 65+ (limited) |
| **Monthly Income** | 40,000+ BDT |
| **Employment Type** | Salaried / Self-employed |
| **Credit Score** | Good (>650) |
| **Documents** | NID + Salary Slip + Tax Certificate |
| **Shariah Compliance** | No interest charges, profit-sharing on credit |

---

## 7. 🧩 Graph-Based Reasoning

Graphs are **deterministic reasoning flows**, not ML.

### 7.0 Graph Architecture Overview

**1 Root Graph + 5 Task Graphs**

```
Graph-0 (Conversation Manager)  ← always running
   |
   |-- invokes Graph-1 (Slot)
   |-- invokes Graph-2 (Eligibility)
   |-- invokes Graph-3 (Product)
   |-- invokes Graph-4 (Comparison)
   |-- invokes Graph-5 (RAG)
```

**✅ Only Graph-0 is allowed to invoke other graphs**

---

### 7.1 GRAPH-0️⃣: CONVERSATION MANAGER GRAPH (ROOT)

**Purpose**
- Routing + orchestration only

**Invoked**
- 👉 **ALWAYS** (every user message)

**🔷 Nodes**
```
START
  |
  v
parse_message
  |
  v
detect_intent
  |
  v
check_missing_slots
  |
  v
route_graph
  |
  v
END
```

**🔷 Edges (CRITICAL)**
```
START → parse_message

parse_message → detect_intent

detect_intent → check_missing_slots

check_missing_slots 
   ├─ if missing_slots != [] → route_graph(slot_graph)
   └─ else → route_graph(by_intent)

route_graph
   ├─ if intent == "eligibility" → invoke Eligibility Graph
   ├─ if intent == "explore" → invoke Product Graph
   ├─ if intent == "compare" → invoke Comparison Graph
   ├─ if intent == "explain" → invoke RAG Graph

route_graph → END
```

---

### 7.2 GRAPH-1️⃣: SLOT COLLECTION GRAPH

**Purpose**
- Ask questions until required fields are filled

**Invoked WHEN**
- `missing_slots != []`

**🔷 Nodes**
```
START
  |
  v
identify_missing_slot  ◄─────────────┐
  |                                  |
  ├─ if missing_slots == [] → END    |
  |                                  |
  └─ else:                           |
      |                              |
      v                              |
      ask_question                   |
      |                              |
      v                              |
      parse_user_answer              |
      |                              |
      v                              |
      update_state                   |
      |                              |
      └──────────────────────────────┘
```

**🔷 Edges**
```
START → identify_missing_slot

identify_missing_slot
   ├─ if missing_slots == [] → END
   └─ else → ask_question

ask_question → parse_user_answer

parse_user_answer → update_state

update_state → identify_missing_slot  [LOOP BACK]
```

---

### 7.3 GRAPH-2️⃣: ELIGIBILITY GRAPH

**Purpose**
- Apply deterministic banking rules

**Invoked WHEN**
- `intent == "eligibility"` AND `missing_slots == []`

**🔷 Nodes**
```
START
  |
  v
validate_inputs
  |
  ├─ if missing → RETURN to Graph-0
  |
  └─ else:
      |
      v
      apply_rules
      |
      v
      filter_products
      |
      v
      store_eligible_products
      |
      v
      END
```

**🔷 Edges**
```
START → validate_inputs

validate_inputs
   ├─ if missing → RETURN to Graph-0
   └─ else → apply_rules

apply_rules → filter_products

filter_products → store_eligible_products

store_eligible_products → END
```

**Used heavily for:**
- Credit cards
- Profit calculations
- High-value schemes

---

### 7.4 GRAPH-3️⃣: PRODUCT RETRIEVAL GRAPH

**Purpose**
- Fetch + display structured product info

**Invoked WHEN**
- `intent == "explore"` OR `eligible_products` already exist

**🔷 Nodes**
```
START
  |
  v
build_query
  |
  v
fetch_products
  |
  v
rank_products
  |
  v
format_response
  |
  v
END
```

**🔷 Edges**
```
START → build_query
build_query → fetch_products
fetch_products → rank_products
rank_products → format_response
format_response → END
```

---

### 7.5 GRAPH-4️⃣: COMPARISON GRAPH

**Purpose**
- Multi-step reasoning across products

**Invoked WHEN**
- `intent == "compare"`

**🔷 Nodes**
```
START
  |
  v
select_products
  |
  v
normalize_attributes
  |
  v
compare_features
  |
  v
apply_religious_constraints
  |
  v
generate_comparison
  |
  v
END
```

**🔷 Edges**
```
START → select_products
select_products → normalize_attributes
normalize_attributes → compare_features
compare_features → apply_religious_constraints
apply_religious_constraints → generate_comparison
generate_comparison → END
```

---

### 7.6 GRAPH-5️⃣: RAG / EXPLANATION GRAPH

**Purpose**
- Explain policies, Shariah rules, interest, regulatory requirements

**Invoked WHEN**
- `intent == "explain"` OR user asks WHY / HOW

**🔷 Nodes**
```
START
  |
  v
retrieve_documents
  |
  v
grounded_generation
  |
  v
END
```

**🔷 Edges**
```
START → retrieve_documents
retrieve_documents → grounded_generation
grounded_generation → END
```

---

### 7.7 🔁 HOW THEY EXECUTE TOGETHER (FINAL EXECUTION FLOW)

**Example 1: Account Opening Query**

```
User: "I am 17, Islami, low deposit — what can I open?"

Graph-0 (Conversation Manager)
  → detects intent = "eligibility"
  → detects banking_type = "islami"
  → detects missing_slots = ["income", "deposit"]
  → invokes Graph-1 (Slot)
      → asks "What's your monthly income?" & "How much to deposit?"
      → fills user_profile.income & user_profile.deposit
      → returns to Graph-0
  → Graph-0 invokes Graph-2 (Eligibility)
      → validates: age, banking_type, income, deposit
      → applies age rule (age < 18 → student accounts only)
      → applies Islami constraint (no interest-based products)
      → filters eligible_products list
      → stores in state
  → Graph-0 invokes Graph-3 (Product)
      → fetches eligible_products from state
      → formats response with product names
      → returns to Graph-0
  → Graph-0 responds to user with options
```

**Example 2: Comparison Request**

```
User: "Compare Conventional vs Islami savings for me"

Graph-0 (Conversation Manager)
  → detects intent = "compare"
  → detects banking_type = None (both types)
  → detects missing_slots = ["product_category", "product_type"]
  → invokes Graph-1 (Slot)
      → asks "Savings or Investment?" & "Accounts or Schemes?"
      → fills product_category & product_type
      → returns to Graph-0
  → Graph-0 invokes Graph-4 (Comparison)
      → selects conventional & islami products (same category/type)
      → normalizes features (profit vs interest, sharia vs conventional)
      → compares side-by-side (min_balance, rates, features)
      → applies religious_constraints
      → generates comparison table
      → returns to Graph-0
  → Graph-0 [OPTIONALLY] invokes Graph-5 (RAG)
      → retrieves Shariah docs explaining profit-sharing
      → retrieves FAQs on interest restrictions
      → generates grounded explanation
      → returns to Graph-0
  → Graph-0 responds with full comparison + explanation
```

**Example 3: Policy Explanation**

```
User: "Why can't I get interest on Islami accounts?"

Graph-0 (Conversation Manager)
  → detects intent = "explain"
  → detects banking_type = None (general question)
  → detects missing_slots = []
  → invokes Graph-5 (RAG)
      → retrieves Shariah compliance documentation
      → retrieves FAQs on profit-sharing vs interest
      → retrieves policy documents on Islamic banking
      → generates grounded explanation (NO hallucination)
      → returns to Graph-0
  → Graph-0 responds with Shariah-compliant explanation
```

---

## 8. 🤖 Domain Agents

Each agent:

* Knows **only its domain**
* Reads shared state
* Uses structured + RAG knowledge
* Produces grounded responses

Examples:

* `islami.save.agent`
* `conventional.credit_card.agent`

---

## 9. 🚀 Execution Flow (End-to-End)

1. User sends message → `/chat`
2. Normalize text
3. Detect intent + product classification
4. Update conversation state
5. Route to domain agent
6. Agent queries knowledge / graphs
7. Response generated
8. State updated

---

## 10. 🧩 Why This Architecture Works

* Clear separation of **domain knowledge**
* Deterministic, explainable decisions
* Scales to new products easily
* Islami vs Conventional logic never mixes incorrectly
* Future-ready for ML upgrades

---

## 11. ✅ Next Natural Extensions

* Multilingual (Bangla + English)
* Admin UI for product updates
* Analytics on user intents
* LLM fine-tuning for intent detection

---

📌 **This document is the source of truth for implementation.**

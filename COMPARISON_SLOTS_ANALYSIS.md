# 📊 COMPARISON SLOTS ANALYSIS

Based on analysis of product knowledge files and existing slot conventions, here are the **comparison-specific slots** that ComparisonGraph should collect before narrowing products.

---

## Products Analysis Summary

### Deposit Schemes (Conventional)
- **Prime Fixed Deposit (FD)**: Lump sum, 1-36 months tenors, 7-8% interest
- **Prime Edu DPS**: Monthly deposits, 5-20 year tenors, 9% fixed, education-focused
- **Prime Kotipoti DPS**: Monthly deposits, 5-15 year tenors, 9% interest, wealth-building
- **Prime Millionaire Scheme**: Monthly fixed installments, 5-12 year tenors, 6-7% interest
- **Prime Deposit Premium Scheme**: Specialized scheme with premium features
- **Prime Double Benefit Scheme**: Multi-benefit scheme
- **Prime Fixed Deposit Plus**: Enhanced FD with additional features
- **Prime I-First FD**: First-time FD scheme
- **Prime Lakhopoti Scheme**: Large amount scheme
- **Prime Laksma Puron Scheme**: Comprehensive scheme
- **Prime Monthly Income Scheme**: Monthly income generation

### Deposit Accounts (Conventional)
- **Prime First Account**: Savings account, minimum balance 1,000, age 13+
- **Prime 50+ Savings Account**: Age-specific
- **Prime Current Account**: Business accounts
- **Prime Atlas FC Account**: Mariners/seafarers, multi-currency

### Islamic Products
- **Prime Hasanah Term Deposit**: 1-36 months, Mudaraba-based, lump sum
- **Prime Hasanah Edu DPS**: Monthly, education-focused, Islamic
- **Prime Hasanah Laksma Puron DPS**: Long-term Islamic DPS
- **Prime Hasanah Monthly Income Scheme**: Monthly income, Islamic

### Key Differences in Dimensions

| Dimension | Values | Impact on Comparison |
|-----------|--------|----------------------|
| **Deposit Type** | Lump sum (FD) vs Monthly (DPS) | Determines affordability & goal alignment |
| **Tenure** | 1-36 months (FD), 5-20 years (DPS) | Critical for financial planning |
| **Interest/Profit** | 6-9% depending on product | Return expectations |
| **Purpose** | General, Education, Wealth-building, Income | User's goal alignment |
| **Banking Type** | Conventional vs Islamic | Shariah compliance requirement |
| **Income Generation** | Lump sum maturity vs Monthly income | Cash flow preferences |

---

## Recommended Comparison Slots

### Core Slots (MUST COLLECT)

| Slot | Type | Description | Examples | Why Important |
|------|------|-------------|----------|---------------|
| `comparison_banking_type` | enum | Conventional / Islamic / Both | "Islamic", "Conventional", "No preference" | Determines product pool (HARD constraint per COMPARISON_RULES.md) |
| `comparison_deposit_frequency` | enum | How user wants to save | "lump_sum", "monthly", "flexible" | Separates FD (lump sum) from DPS (monthly) - fundamental difference |
| `comparison_tenure_range` | enum | Timeline for savings | "short" (1-3mo), "medium" (6-12mo), "long" (5+ years) | Many products have specific tenure ranges |
| `comparison_purpose` | enum | Goal for the savings | "general", "education", "wealth_building", "retirement", "income_generation" | Matches to specialized schemes (Edu DPS, Monthly Income, etc.) |

### Secondary Slots (SHOULD COLLECT)

| Slot | Type | Description | Examples | Why Important |
|------|------|-------------|----------|---------------|
| `comparison_interest_priority` | enum | Return expectations | "high_returns", "moderate", "stable", "flexible" | Users may prioritize differently |
| `comparison_flexibility_priority` | enum | Access/withdrawal needs | "high_access", "moderate", "locked_in", "flexible" | Some schemes offer loan facilities, early encashment |
| `comparison_feature_priorities` | list[string] | Specific features of interest | ["auto_renewal", "loan_facility", "guaranteed_returns", "tax_benefits"] | Narrows to products with desired features |

### Optional Slots (NICE TO HAVE)

| Slot | Type | Description | Examples | Why Important |
|------|------|-------------|----------|---------------|
| `comparison_initial_budget` | float | Amount willing to deposit | 50000, 100000, 500000 | Some products have minimum/maximum limits |
| `comparison_monthly_budget` | float | For DPS schemes, monthly capacity | 1000, 5000, 10000 | DPS requires affordable monthly commitment |

---

## Slot Collection Flow for ComparisonGraph

### Phase 1: Narrow by Core Dimensions
```
1. Ask banking_type → "Do you prefer Islamic or Conventional banking?"
   Result: Filter pool by domain
   
2. Ask deposit_frequency → "Would you prefer lump sum or monthly deposits?"
   Result: Separate FD (lump sum) from DPS (monthly) paths
   
3. Ask tenor_range → "What's your timeline?"
   Result: Filter by available tenors
   
4. Ask purpose → "What's the goal of your savings?"
   Result: Filter by specialized schemes (education, income, etc.)
```

### Phase 2: Refine by Preferences
```
5. Ask interest_priority → "Is high returns your priority, or stability?"
   Result: Rank products by rates
   
6. Ask flexibility_priority → "Do you need access to funds before maturity?"
   Result: Filter for loan/encashment options
   
7. Ask feature_priorities → "Any specific features important to you?"
   Result: Narrow to 2-3 most relevant products
```

---

## Example Narrowing Scenarios

### Scenario 1: Education-Focused Parent
- **Input**: "Compare deposit schemes for my child's education"
- **Questions to ask**:
  1. "Conventional or Islamic banking?" → Islamic
  2. "Can you invest monthly?" → Yes, monthly
  3. "How many years?" → 15 years
  4. "Any preference on features?" → Education-focused
  
- **Result**: 
  - Prime Hasanah Edu DPS ✓
  - Prime Edu DPS ✓
  - (All other schemes filtered out)

### Scenario 2: Monthly Income Seeker
- **Input**: "I want to compare schemes that give me monthly income"
- **Questions to ask**:
  1. "Conventional or Islamic?" → Flexible
  2. "Monthly income preferred?" → Yes
  3. "How long to invest?" → 5-10 years
  4. "Monthly income amount needed?" → 10,000 BDT
  
- **Result**:
  - Prime Monthly Income Scheme (Conventional) ✓
  - Prime Hasanah Monthly Income Scheme (Islamic) ✓
  - (DPS schemes filtered - they pay lump sum at maturity)

### Scenario 3: Lump Sum Investor
- **Input**: "Compare fixed deposit schemes"
- **Questions to ask**:
  1. "Banking type?" → Conventional
  2. "Confirm lump sum?" → Yes
  3. "How long?" → 12 months
  4. "Any specific features?" → Auto-renewal preferred
  
- **Result**:
  - Prime Fixed Deposit ✓
  - Prime Fixed Deposit Plus ✓
  - (DPS schemes filtered - they require monthly deposits)

---

## Implementation Considerations

### 1. Slot-Based Filtering Logic
```python
# In identify_products_node or new slot_collection_node

def filter_products_by_slots(all_products, slots):
    """
    Filter products based on collected comparison slots.
    Applied in priority order.
    """
    
    filtered = all_products
    
    # 1. Banking type (HARD filter)
    if slots.get('comparison_banking_type') != 'flexible':
        filtered = [p for p in filtered 
                    if p['banking_type'] == slots['comparison_banking_type']]
    
    # 2. Deposit frequency (HARD filter)
    if slots.get('comparison_deposit_frequency') == 'monthly':
        filtered = [p for p in filtered if p['payment_type'] == 'monthly']
    elif slots.get('comparison_deposit_frequency') == 'lump_sum':
        filtered = [p for p in filtered if p['payment_type'] == 'lump_sum']
    
    # 3. Purpose (SOFT filter - narrows but doesn't eliminate)
    if slots.get('comparison_purpose') == 'education':
        filtered = sort_by_match(filtered, purpose='education')
    
    # 4. Features (SOFT filter - bonus points)
    if slots.get('comparison_feature_priorities'):
        filtered = sort_by_feature_match(filtered, slots['comparison_feature_priorities'])
    
    return filtered[:3]  # Return top 3 matches
```

### 2. Questions to Ask in ComparisonGraph

**Question 1: Banking Type**
```
"Would you prefer to compare Islamic (Shariah-compliant) or Conventional banking products, 
or are you flexible between both?"

Options: Islamic | Conventional | No preference
```

**Question 2: Deposit Frequency**
```
"Do you prefer a lump-sum deposit (like FDs - you deposit once) or monthly deposits 
(like DPS - you save every month)?"

Options: Lump sum | Monthly | Flexible
```

**Question 3: Timeline**
```
"What's your timeline for this savings goal?"

Options: 
- Short-term (1-3 months)
- Medium-term (6-12 months)
- Long-term (2-5 years)
- Very long-term (5+ years)
```

**Question 4: Purpose**
```
"What's the main purpose of your savings?"

Options:
- General savings
- Child's education
- Building wealth/retirement
- Monthly income generation
- Other (please specify)
```

### 3. Comparison-Specific Prompts Needed

Update `/app/prompts/conversation/comparison.py` to add:
- `COLLECT_COMPARISON_SLOTS_PROMPT`: Determines which slots are missing and what to ask
- `FILTER_PRODUCTS_BY_SLOTS_PROMPT`: Generates explanation of why certain products are recommended
- `REFINE_COMPARISON_PROMPT`: If 2+ products after filtering, ask preference questions

---

## Next Steps

1. ✅ Add comparison slots to `ConversationState` (banking_type, deposit_frequency, tenure_range, purpose, etc.)
2. ✅ Add `slot_collection_node` before `identify_products_node` in ComparisonGraph
3. ✅ Implement `filter_products_by_slots()` logic
4. ✅ Create slot collection prompts in `/app/prompts/conversation/comparison.py`
5. ✅ Update `identify_products_node` to use filtered products instead of raw vector search
6. ✅ Test with vague queries: "compare two deposit schemes" → Should ask 4 clarifying questions first

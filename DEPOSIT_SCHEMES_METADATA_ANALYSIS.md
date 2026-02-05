# Deposit Schemes Metadata Analysis

## Overview
Analysis of deposit scheme MD files to identify common fields and metadata that should be extracted and indexed for better RAG search accuracy.

---

## Common Fields Across All Deposit Schemes

### 1. **Product Identifiers**
- **Product Name**: prime_kotipoti_dps, prime_fixed_deposit, prime_laksma_puron_scheme, etc.
- **Product Type**: DPS (Deposit Pension Scheme), FD (Fixed Deposit), Installment Scheme
- **Tagline/Slogan**: Marketing phrase for the product

### 2. **Return Metrics** 
#### Conventional Schemes:
- **Interest Rate**: 9%, 6-7%, 7-8% (explicitly stated)
- **Interest Rate Range**: e.g., "typically 7-8% annually"
- **Tenor-Based Rates**: Different tenors may have different rates
  - Example: Millionaire Scheme: 5-7 years @ 6%, 10-12 years @ 7%
  - Example: Kotipoti DPS: All tenors @ 9%
  - Example: Fixed Deposit: 1-3 months, 6 months, 12 months, 24 months, 36 months with varying rates

#### Islamic Schemes:
- **Profit Rate**: 6%, 9% (NOT "interest rate")
- **Islamic Term**: "Profit" (Mudaraba principle-based)
- **Shari'ah Compliance**: Mentioned explicitly
- **Tenor-Based Profit**: Fixed across tenors or varying
  - Example: Hasanah Edu DPS: 9% profit across all tenors (5/10/15/20 years)
  - Example: Hasanah Laksma Puron DPS: 6% profit across all tenors (3/4/5 years)

### 3. **Deposit Type/Structure**

| Field | Conventional | Islamic |
|-------|---|---|
| **Lump Sum Deposit** | Fixed Deposit | Not common |
| **Monthly Installment** | DPS, Millionaire, Laksma Puron | Edu DPS, Laksma Puron DPS |
| **Fixed Monthly Amount** | Kotipoti DPS, Millionaire Scheme | Edu DPS |
| **Custom Goal-Based** | Laksma Puron (variable monthly) | Laksma Puron DPS (variable monthly) |
| **Initial Deposit + Monthly** | Kotipoti DPS (with BDT 1 lac reduces monthly) | Edu DPS (BDT 500 minimum monthly) |

### 4. **Tenor/Duration Options**

#### Conventional:
- **Fixed Deposit**: 1, 3, 6, 12, 24, 36 months (short term, 1-36 months)
- **Kotipoti DPS**: 5, 7, 10, 12, 15 years (long term)
- **Laksma Puron**: 3, 4, 5 years (medium term, customizable)
- **Millionaire Scheme**: 5, 7, 10, 12 years (long term)

#### Islamic:
- **Edu DPS**: 5, 10, 15, 20 years (education-focused, long term)
- **Laksma Puron DPS**: 3, 4, 5 years (medium term, customizable)

### 5. **Purpose/Use Case**

Explicitly stated target audience:

| Scheme | Purpose |
|--------|---------|
| Laksma Puron | **Custom goal saving** (wedding, education, business, home) |
| Fixed Deposit | Conservative saving, lump sum investment |
| Kotipoti DPS | Long-term wealth accumulation ("crores") |
| Millionaire Scheme | First million achievement, salaried individuals |
| Edu DPS | Education fund for children |
| Monthly Income Scheme | Regular income generation |
| Double Benefit/Deposit Premium | Savings + insurance protection |

### 6. **Eligibility & Demographics**

| Field | Values |
|-------|--------|
| **Minimum Age** | 18 years (most schemes) |
| **Maximum Age** | No limit (some highlight 50+ accounts) |
| **Employment Type** | Any, Salaried, Business, Professional |
| **Minimum Deposit** | BDT 10,000 (FD), BDT 500/month (Edu DPS), BDT 1,275/month (Laksma Puron) |
| **Account Requirement** | Active linked Current/Savings with Prime Bank |
| **Minor Support** | Parent/legal guardian required |

### 7. **Additional Features** (Common Across Schemes)

- **Loan Facility**: Up to 90% or 100% of deposited amount
- **Auto-Renewal**: FD typically has auto-renewal option
- **Early Encashment**: With forfeiture rules (tiered based on tenure completed)
- **Multiple Schemes**: Can open multiple accounts in same name
- **Auto-Deduction**: Monthly payments automatically deducted from linked account

### 8. **Key Differentiators to Extract**

| Aspect | Importance | Values |
|--------|-----------|--------|
| **Deposit Frequency** | HIGH | Lump Sum vs Monthly vs Custom |
| **Return Type** | HIGH | Interest (Conventional) vs Profit (Islamic) |
| **Return Rate** | HIGH | 6%, 7%, 9%, varying by tenor |
| **Tenor Length** | HIGH | 1 month to 20 years |
| **Purpose/Goal** | HIGH | Wedding, Education, Income, Wealth, Custom |
| **Monthly Amount** | MEDIUM | Fixed amount vs Custom vs Range |
| **Accessibility** | MEDIUM | Loan facility percentage, withdrawal rules |
| **Religious** | MEDIUM | Islamic Mudaraba vs Conventional Interest |
| **Target Demographic** | MEDIUM | Age, employment, income level |
| **Maturity Value** | LOW | Calculated from interest/tenure |

---

## RAG Metadata Extraction Recommendations

### Current Issues:
1. **Missing Return Rate in Metadata**: RAG doesn't extract interest/profit rate as structured metadata
2. **Missing Deposit Type**: Not indexed whether scheme is lump-sum, monthly, or custom
3. **Missing Purpose Field**: Goal/use-case not indexed separately
4. **Missing Tenor Details**: Tenor options not structured in metadata
5. **Missing Islamic Flag**: No distinction between Islamic/Conventional in structured metadata

### Recommended Metadata Fields to Add:

```python
{
    # Existing fields
    'product_name': 'prime_laksma_puron_scheme',
    'banking_type': 'conventional',
    'category': 'save',
    'product_id': '',
    'path': '/app/app/knowledge/products/conventional/save/deposit_schemes/prime_laksma_puron_scheme.md',
    
    # NEW FIELDS TO ADD
    'scheme_type': 'monthly_installment_custom_goal',  # lump_sum | monthly_fixed | monthly_custom | mixed
    'return_type': 'interest',  # 'interest' for conventional, 'profit' for islamic
    'return_rate': '6%',  # Consistent return rate
    'tenor_options': ['3 years', '4 years', '5 years'],  # List of available tenors
    'tenor_range_years': [3, 5],  # Min to max years
    'minimum_monthly_deposit': 'BDT 1,275',  # For monthly schemes
    'minimum_lump_sum': 'BDT 10,000',  # For lump sum (if applicable)
    'primary_purpose': 'custom_goal_savings',  # wedding | education | income | wealth | custom
    'secondary_purposes': ['wedding', 'education', 'business', 'home_improvement'],
    'target_demographic': 'anyone',  # anyone | salaried | retired | professionals | nrb_families
    'age_preference': '18+',  # Any specific age targeting
    'loan_facility_percent': '100%',  # Up to X% of deposited amount
    'special_features': ['auto_deduction', 'loan_facility', 'multiple_schemes'],
    'islamic_compliant': False,  # True for Hasanah products
}
```

### Enhanced Search Query Terms:

When user mentions:
- **"500000 wedding 3 years"** → Search for: `return_rate`, `tenor_options`, `primary_purpose: 'custom_goal_savings'`
- **"monthly income"** → Search for: `primary_purpose: 'income'`, `return_type`, `monthly_fixed`
- **"education fund 15 years"** → Search for: `primary_purpose: 'education'`, `tenor_range_years: 15`
- **"specific goal amount"** → Search for: `scheme_type: 'monthly_custom'`, `primary_purpose: 'custom_goal_savings'`
- **"Islamic banking"** → Search for: `islamic_compliant: True`, `return_type: 'profit'`

---

## Field Definitions

### Scheme Type Classification

1. **Lump Sum (FD-like)**
   - Single upfront deposit
   - Fixed tenor
   - Maturity payout
   - Example: Prime Fixed Deposit

2. **Monthly Fixed**
   - Fixed monthly amount
   - Fixed tenor
   - Determined maturity value
   - Example: Kotipoti DPS (BDT 132,782/month for 5 years)

3. **Monthly Custom**
   - Customer-defined goal amount
   - Customer-defined tenor (3-5 years typically)
   - Monthly amount calculated automatically
   - Example: Laksma Puron, Laksma Puron DPS

4. **Mixed**
   - Initial lump sum + monthly installments
   - Reduces monthly payment obligation
   - Example: Kotipoti DPS with BDT 1 lac initial deposit

### Return Type (Conventional vs Islamic)

**Conventional**: "Interest"
- Charged on principal
- Typical rate: 6-9% annually
- Example: Prime Fixed Deposit @ 7-8%, Kotipoti DPS @ 9%

**Islamic**: "Profit" (Mudaraba Model)
- Profit-sharing partnership
- Same effective rate: 6-9% annually
- Shariah-compliant
- Example: Hasanah Edu DPS @ 9% profit, Hasanah Laksma Puron DPS @ 6% profit

---

## Comparison Matrix: Key Schemes

| Scheme | Type | Return | Tenor | Min Deposit | Purpose |
|--------|------|--------|-------|-------------|---------|
| Fixed Deposit | Lump Sum | Interest 7-8% | 1-36 months | BDT 10K | Conservative saving |
| Kotipoti DPS | Monthly Fixed | Interest 9% | 5-15 years | ~BDT 27-132K/month | Long-term wealth |
| Laksma Puron | Monthly Custom | Interest 6% | 3-5 years | Variable (goal-based) | **Custom goal saving** |
| Millionaire | Monthly Fixed | Interest 6-7% | 5-12 years | BDT 4.5-14.5K/month | First million |
| Edu DPS | Monthly Fixed | Interest 9% | 5-20 years | BDT 500+/month | **Education fund** |
| Laksma Puron DPS | Monthly Custom | **Profit 6%** | 3-5 years | Variable (goal-based) | **Custom goal (Islamic)** |
| Edu DPS Hasanah | Monthly Fixed | **Profit 9%** | 5-20 years | BDT 500+/month | **Education fund (Islamic)** |

---

## Recommendations for Bot Improvement

### 1. **Enhance RAG Indexing**
   - Extract and index return_rate, return_type, scheme_type as separate metadata fields
   - Create searchable tags for purpose, tenor options, and demographic targeting
   - Add Islamic compliance flag to distinguish Conventional vs Islamic banking

### 2. **Improve Search Matching**
   - When user says "goal amount + tenure", specifically search for `scheme_type: 'monthly_custom'`
   - Match `return_rate` in search when comparing schemes
   - Use `primary_purpose` field for purpose-based recommendations

### 3. **Better Recommendation Logic**
   - If user mentions specific goal + tenure → prioritize Laksma Puron schemes (both Islamic and Conventional)
   - If user mentions education → prioritize Edu DPS schemes
   - If user mentions regular income generation → prioritize Monthly Income Scheme
   - If Islamic banking mentioned → filter to Hasanah (Islamic) products only

### 4. **Dynamic Query Construction**
   - Build search queries that include return_rate matching
   - Add tenor range matching (e.g., "3 years" → search 3-5 year schemes)
   - Include purpose keywords from user intent

---

## Islamic vs Conventional Terminology

| Aspect | Conventional | Islamic |
|--------|---|---|
| Return on investment | **Interest** | **Profit** |
| Partnership model | Debtor-creditor | Mudaraba (profit-sharing) |
| Typical rate | 6-9% interest | 6-9% profit |
| Shari'ah compliance | Not required | Explicitly mentioned |
| Schemes in KB | Prime [scheme name] | Prime Hasanah [scheme name] |
| Examples | Kotipoti DPS, Laksma Puron | Hasanah Edu DPS, Hasanah Laksma Puron DPS |

---

## Action Items for Implementation

- [ ] Enhance `rag_retriever.py` to extract and index return_rate, scheme_type, purpose, tenor_options
- [ ] Update metadata extraction in `_extract_metadata()` function
- [ ] Modify RAG filters to support purpose, return_rate, and scheme_type matching
- [ ] Update product recommendation prompt to use structured fields instead of free text
- [ ] Create separate search paths for "custom goal + tenure" queries to prioritize Laksma Puron
- [ ] Test RAG search with return_rate, purpose, and tenor_range filters

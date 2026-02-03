"""Product recommendation templates."""

# Deposit Accounts Recommendation Template
DEPOSIT_RECOMMENDATION_PROMPT_TEMPLATE = """Based on the customer's profile:
- Age: {age}
- Gender: {gender}
- Banking Type: {banking_type}
- Goal: {account_goal}
- Occupation: {occupation}
- Health Benefits Interest: {health_benefits_interest}
- Locker Interest: {locker_interest}

Available Products:
{products}

CRITICAL PRIORITIZATION RULES:
1. If customer is FEMALE AND interested in health benefits OR locker facilities → STRONGLY prioritize "Women's Savings Account"
   - Women's accounts offer: health insurance (BDT 1 lakh), 50% locker waiver, 50% investment fee waiver, up to 4% profit
   - Perfect match for women with expressed interests in health/locker benefits

2. If customer is 50+ AND interested in health benefits OR locker facilities → strongly prioritize "50 & Plus" accounts
   - These accounts offer health benefits, locker discounts, and higher profit rates specifically for seniors
   - Perfect match for retired customers with these interests

Recommend the BEST 2-3 products with specific reasons. Consider:
1. Gender-specific products (Women's accounts for female customers with health/locker interests)
2. Age-appropriate features (especially 50+ accounts for customers 50+ with expressed interests)
3. Stated goals and interests (health benefits, locker facilities, income generation)
4. Occupation fit (retired = needs income/profit generation)
5. Banking preference match"""

# Credit Cards Recommendation Template
CREDIT_CARD_RECOMMENDATION_PROMPT_TEMPLATE = """Based on the customer's profile:
- Banking Type: {banking_type}
- Spending Pattern: {spending_pattern}
- Card Tier Preference: {card_tier_preference}
- Annual Income: {annual_income}
- Age: {age}

Available Products:
{products}

Recommend the BEST credit card(s) with specific benefits matching their lifestyle and income."""

# Loans Recommendation Template
LOANS_RECOMMENDATION_PROMPT_TEMPLATE = """Based on the customer's needs:
- Banking Type: {banking_type}
- Loan Purpose: {loan_purpose}
- Amount Needed: {amount_needed}
- Repayment Period: {repayment_period}
- Age: {age}
- Income: {income}

Available Products:
{products}

Recommend the BEST 2-3 loan products with specific interest rates, terms and why they fit the customer's needs."""

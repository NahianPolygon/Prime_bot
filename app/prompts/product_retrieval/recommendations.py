"""Product recommendation templates."""

# Deposit Accounts Recommendation Template
DEPOSIT_RECOMMENDATION_PROMPT_TEMPLATE = """Based on the customer's profile:
- Age: {age}
- Gender: {gender}
- Banking Type: {banking_type}
- Remittance Status: {remittance_status}
- Goal: {account_goal}
- Occupation: {occupation}
- Health Benefits Interest: {health_benefits_interest}
- Locker Interest: {locker_interest}

Available Products:
{products}

CRITICAL PRIORITIZATION RULES:
1. If customer is receiving REMITTANCES (NRB families) → STRONGLY prioritize "Porijon Savings Account"
   - Porijon is designed specifically for NRB remittance recipient families
   - Offers: automatic life insurance (25K-100K based on remittance amount), 3% profit, monthly payments

2. If customer is FEMALE AND interested in health benefits OR locker facilities → STRONGLY prioritize "Women's Savings Account"
   - Women's accounts offer: health insurance (BDT 1 lakh), 50% locker waiver, 50% investment fee waiver, up to 4% profit

3. If customer is 50+ AND interested in health benefits OR locker facilities → prioritize "50 & Plus" accounts
   - Offers health benefits, locker discounts, and higher profit rates for seniors

RESPOND IN THIS EXACT FORMAT - RECOMMEND EXACTLY 2 PRODUCTS:
Use simple text with line breaks. NO markdown, NO asterisks, NO special formatting.
INCLUDE SPECIFIC PRODUCT DETAILS: interest rates, minimum balance, locker info, monthly benefits, withdrawal flexibility.
MAKE RECOMMENDATIONS CONVINCING by explaining HOW each product specifically matches the customer's goals.

RECOMMENDED DEPOSIT PRODUCTS

1. [Full Readable Product Name]
----------------------
Why This Product:
• [How it specifically addresses the customer's goal]
• [Specific benefit that matches their needs (e.g., locker facility if interested)]
• [Concrete advantage over alternatives (e.g., interest rate, minimum balance, flexibility)]
----------------------
Key Features:
• Interest Rate: [Rate]
• Minimum Balance: [Amount]
• Locker Facility: [Yes/No and details if applicable]
• Monthly/Yearly Benefit: [Specific benefit]
• Withdrawal Flexibility: [Details]
• Other Perks: [Any additional benefits]

======================

2. [Full Readable Product Name]
----------------------
Why This Product:
• [How it specifically addresses the customer's goal]
• [Specific benefit that matches their needs]
• [Concrete advantage that makes it competitive]
----------------------
Key Features:
• Interest Rate: [Rate]
• Minimum Balance: [Amount]
• Locker Facility: [Yes/No and details if applicable]
• Monthly/Yearly Benefit: [Specific benefit]
• Withdrawal Flexibility: [Details]
• Other Perks: [Any additional benefits]
"""

# Credit Cards Recommendation Template
CREDIT_CARD_RECOMMENDATION_PROMPT_TEMPLATE = """Based on the customer's profile:
- Banking Type: {banking_type}
- Spending Pattern: {spending_pattern}
- Card Tier Preference: {card_tier_preference}
- Annual Income: {annual_income}
- Age: {age}

Available Products:
{products}

RESPOND IN THIS EXACT FORMAT - RECOMMEND EXACTLY 2 CREDIT CARDS:
Use simple text with line breaks. NO markdown, NO asterisks, NO special formatting.
INCLUDE SPECIFIC PRODUCT DETAILS: annual fee, credit limit, rewards, cashback, interest rate.
MAKE RECOMMENDATIONS CONVINCING by explaining HOW each card matches the customer's spending pattern and income.

RECOMMENDED CREDIT CARDS

1. [Full Readable Card Name]
----------------------
Why This Card:
• [How it matches the customer's spending pattern]
• [How it aligns with their income level and card tier preference]
• [Specific benefit that makes it attractive for their use case]
----------------------
Key Features:
• Annual Fee: [Amount or "Waived"]
• Credit Limit: [Range based on income]
• Rewards/Cashback: [Specific percentage or benefit]
• Interest Rate: [APR or range]
• Joining Bonus: [If applicable]
• Other Perks: [Concierge, insurance, etc.]

======================

2. [Full Readable Card Name]
----------------------
Why This Card:
• [How it matches the customer's spending pattern]
• [How it aligns with their income level]
• [Specific benefit or advantage over Card 1]
----------------------
Key Features:
• Annual Fee: [Amount or "Waived"]
• Credit Limit: [Range based on income]
• Rewards/Cashback: [Specific percentage or benefit]
• Interest Rate: [APR or range]
• Joining Bonus: [If applicable]
• Other Perks: [Concierge, insurance, etc.]

======================

2. [Full Readable Card Name]
----------------------
Why This Card:
• [How it matches the customer's spending pattern]
• [How it aligns with their income level]
• [Specific benefit or advantage over Card 1]
----------------------
Key Features:
• Annual Fee: [Amount or "Waived"]
• Credit Limit: [Range based on income]
• Rewards/Cashback: [Specific percentage or benefit]
• Interest Rate: [APR or range]
• Joining Bonus: [If applicable]
• Other Perks: [Concierge, insurance, etc.]
"""

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

RESPOND IN THIS EXACT FORMAT - RECOMMEND EXACTLY 2 LOANS:
Use simple text with line breaks. NO markdown, NO asterisks, NO special formatting.
INCLUDE SPECIFIC PRODUCT DETAILS: interest rate, loan amount range, tenure, processing fee, eligibility.
MAKE RECOMMENDATIONS CONVINCING by explaining HOW each loan matches the customer's purpose, amount, and repayment capacity.

RECOMMENDED LOAN PRODUCTS

1. [Full Readable Loan Name]
----------------------
Why This Loan:
• [How it specifically matches the customer's loan purpose]
• [How the loan amount and tenure align with their needs]
• [Specific advantage (competitive rate, flexible repayment, low processing fee)]
----------------------
Loan Details:
• Loan Amount: [Range - minimum to maximum]
• Interest Rate: [Annual percentage or range]
• Repayment Period: [Tenure options in months/years]
• Processing Fee: [Amount or percentage]
• Eligibility Requirement: [Minimum age, income, credit]
• Special Features: [Any additional benefits]

======================

2. [Full Readable Loan Name]
----------------------
Why This Loan:
• [How it specifically matches the customer's loan purpose]
• [How the loan amount and tenure align with their needs]
• [Specific advantage over Loan 1]
----------------------
Loan Details:
• Loan Amount: [Range - minimum to maximum]
• Interest Rate: [Annual percentage or range]
• Repayment Period: [Tenure options in months/years]
• Processing Fee: [Amount or percentage]
• Eligibility Requirement: [Minimum age, income, credit]
• Special Features: [Any additional benefits]
"""

RANK_PRODUCTS_PROMPT = """Rank products by user fit.

Products: {products}
User Profile:
- Age: {age}
- Employment: {employment}
- Income: {income}

Top ranking factors:
1. Eligibility match
2. Benefit alignment
3. Ease of access

Return ranked list with reasoning."""

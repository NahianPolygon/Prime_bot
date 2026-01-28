ASSESS_ELIGIBILITY_PROMPT = """Based on user profile, assess product eligibility.

User Profile:
- Age: {age}
- Employment: {employment}
- Monthly Income: {income}
- Credit Score: {credit_score}

Banking Type: {banking_type}
Product Category: {product_category}

Eligibility rules:
1. Age 18-65, salaried, income 20k+ → savings products
2. Age 21+, income 30k+ → credit products
3. Income 50k+ → investment products
4. Deposit 100k+ → premium products

Return eligible products list with reasoning."""

"""Eligibility checking prompts."""

ELIGIBILITY_CHECK_PROMPT = """Check if user is eligible for these specific products based on their profile.

User Profile:
- Age: {age}
- Employment: {employment}
- Income: {income}

These are the products they're interested in: {products}

Knowledge Context:
{knowledge_context}

For each product, provide:
1. Whether they're eligible
2. Key eligibility requirements
3. Next steps if eligible

Be concise and specific to these products only."""

ELIGIBILITY_REQUEST_INFO_PROMPT = """To check your eligibility, I need a bit more information. What's your age and employment type?"""

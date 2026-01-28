GENERATE_RESPONSE_PROMPT = """Create user-friendly eligibility message.

Eligible Products: {eligible_products}
User: {age} years old, {employment}, {income} BDT/month
Recommendations: {recommendations}

Write concise, encouraging response."""

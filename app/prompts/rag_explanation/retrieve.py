RETRIEVE_DOCUMENTS_PROMPT = """Find relevant product information.

Product: {product}
Banking Type: {banking_type}
User Query: {query}

Retrieve documentation covering:
- Product features and benefits
- Eligibility requirements
- Charges and fees
- Terms and conditions

Return relevant document summaries."""

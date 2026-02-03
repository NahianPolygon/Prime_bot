RANK_PRODUCTS_BY_PROFILE_PROMPT = """Based on the knowledge base below, rank these banking products by suitability.

User Profile:
- Age: {age}
- Income: {income}
- Employment: {employment}

Products: {product_names}

Knowledge Base Context:
{chunks}

Return ranked list from most to least suitable, with brief reason."""

FORMAT_PRODUCT_RESPONSE_PROMPT = """Create a clean product recommendation based on user query.

User Query: {user_query}
Recommended Products: {product_names}

Knowledge Context:
{chunks}

Format response as:
1. 1-2 sentences acknowledging their needs
2. List products as bullet points with key benefit each:
   • Product Name - Key benefit or feature
3. 1-2 sentences with next step

Keep it concise (under 150 words). NO long explanations."""

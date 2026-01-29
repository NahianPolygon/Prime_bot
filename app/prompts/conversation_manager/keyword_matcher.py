KEYWORD_MATCH_PROMPT = """You are a keyword matching expert for banking products.

Determine if a product matches the user's keywords and use cases.

User Keywords: {user_keywords}
User Use Cases: {user_use_cases}

Product Name: {product_name}
Product Quick Match Keywords: {product_keywords}
Product Use Cases: {product_use_cases}
Product Features: {product_features}

Analyze if this product matches what the user is looking for.

Consider:
1. Semantic similarity (not just exact match)
2. Implied features (e.g., "travel benefits" matches "international cards")
3. Common banking terminology
4. Product category alignment

Respond with JSON:
{{"matches": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

IMPORTANT: Return ONLY valid JSON, nothing else:"""

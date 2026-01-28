RETRIEVE_PRODUCTS_PROMPT = """Retrieve and rank banking products.

Banking Type: {banking_type}
Product Category: {product_category}
User Profile: {profile}
Available Products: {available_products}

Rank products by relevance to user profile.
Consider: age, employment, income, existing products."""

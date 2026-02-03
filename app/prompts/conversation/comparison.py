"""Product comparison prompts."""

PREPARE_COMPARISON_PROMPT = """Compare these {num_products} banking products for the user.

User Query: {user_message}
Products: {product_names}

Knowledge Context:
{chunks}

Create friendly comparison highlighting key differences, features, and recommending best fit based on user needs."""

COMPARISON_CLARIFICATION_PROMPT = """To provide a good comparison, could you tell me which types of products you're interested in? 
For example, savings accounts, credit cards, or loans?"""

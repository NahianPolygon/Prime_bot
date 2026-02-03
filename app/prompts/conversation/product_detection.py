"""Product category detection based on user intent."""

DETECT_PRODUCT_TYPE_PROMPT = """Based on this user message, determine which banking product category they're interested in.

User Message: "{message}"

Respond with ONLY one word: either "deposits", "credit_cards", or "loans"

Examples:
- "I want to save money" → deposits
- "I need a card for shopping" → credit_cards
- "I want to borrow some money" → loans
- "What are your investment schemes?" → deposits
- "Can I get a credit card?" → credit_cards
- "Tell me about personal loans" → loans

Respond with just the category name, nothing else."""

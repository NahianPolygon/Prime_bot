"""RAG-based explanation and general Q&A prompts."""

EXPLAIN_WITH_RAG_PROMPT = """Based on banking knowledge base, answer user's question concisely and clearly.

User Question: {user_message}

Knowledge Context:
{knowledge_context}

IMPORTANT: Keep response short and well-structured. Use bullet points for multiple options.
If suggesting products, format as:
• Product Name - Brief description (key feature)
• Product Name - Brief description (key feature)

Do NOT list every detail. Be concise and user-friendly."""

NO_KNOWLEDGE_RESPONSE = """I don't have specific information about that. Could you ask about a product or feature?"""

UNCLEAR_RESPONSE = """I found relevant information about that. Could you be more specific?"""

GREETING_DETECTION_PROMPT = """Classify if the user's message is a greeting/casual message, a slot value response, or a direct banking request.

GREETING includes: "Hello", "Hi", "How are you?", "Hey", "Good morning", "What's up", etc.
SLOT RESPONSE includes: "My age is", "I earn", "I'm employed", "I work as", "I have", any answer to a question like "What is your age?"
REQUEST includes: "Show me", "How many", "Tell me about", "What credit cards", "I want", "I need", etc.

Respond with ONLY one word:
- "GREETING" if it's a casual greeting
- "SLOT" if it's answering a question/providing slot information
- "REQUEST" if it's a direct banking request

User message: {user_message}
"""

GREETING_PROMPT = """You are a helpful banking assistant for Prime Bank. A user has just started a conversation with you.

Provide a warm, welcoming greeting that:
1. Welcomes them to Prime Bank's banking assistant
2. Briefly mentions what you can help with (explore products, check eligibility, compare accounts, explain products)
3. Asks what they would like help with regarding banking

Keep the greeting concise and friendly (2-3 sentences max).

User's message: {user_message}
"""

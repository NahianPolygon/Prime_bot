INTENT_PROMPT = """Analyze user message and classify the intent.

User: {user_message}
Conversation history: {history}

Classify:
1. Intent: explore (browsing products), eligibility (checking qualification), compare (comparing products), explain (product explanation)
2. Banking type: conventional or islami (Islamic/Shariah-compliant)
3. Product category: deposit, credit, investment, or other

Respond with JSON."""

SLOT_VALIDATION_PROMPT = """Based on user intent and profile, determine missing required slots.

Intent: {intent}
User Profile: {profile}
Conversation: {history}

Missing slots needed for {intent}:
- For 'eligibility': may need age, income, employment_type
- For 'compare': may need product_category
- For 'explore': generally needs banking_type and product_category

Respond with JSON with missing_slots array and reason."""

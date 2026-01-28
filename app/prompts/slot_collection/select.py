SELECT_SLOT_PROMPT = """Based on missing slots and conversation context, select the NEXT slot to ask for.

Missing slots (IN PRIORITY ORDER): {missing_slots}
User profile: {profile}
Intent: {intent}
Conversation: {history}

**IMPORTANT**: Select the FIRST slot from the missing slots list above. Do NOT reorder or prioritize differently.
The list is already ordered by priority:
- If banking_type is first, ask about Conventional vs Islamic banking FIRST
- If age is first, ask age FIRST
- If income is first, ask income FIRST
- Always follow the given order

Generate a natural, conversational prompt for the first missing slot."""

SELECT_SLOT_PROMPT = """Based on missing slots and conversation context, select which slot to ask for next.

Missing slots: {missing_slots}
User profile: {profile}
Intent: {intent}
Conversation: {history}

Prioritize: age before income before deposit. Select one and generate a natural prompt."""

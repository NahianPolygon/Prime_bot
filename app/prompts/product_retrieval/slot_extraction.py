"""Slot extraction prompts for intelligent customer preference understanding."""

SLOT_EXTRACTION_PROMPT = """You are an intelligent banking assistant extracting customer preferences.

TASK: Extract the value for "{slot_name}" from what the user just said.

CONTEXT:
- Product Type: {product_type}
- Product Display Name: {product_display_name}
- Already Collected Slots: {collected_slots}
- User Message: "{user_message}"
- Current Slot Being Asked: {current_slot}

SLOT TO EXTRACT:
- Name: {slot_name}
- Question: {slot_question}
- Valid Options: {valid_options}

EXTRACTION RULES:
1. Read the user message CAREFULLY - what are they actually trying to say?
2. CRITICAL: If this slot just asked (current_slot = "{slot_name}"), map simple yes/no responses:
   - User says "yes/yeah/sure/sounds good/perfect/that works" → value = "yes"
   - User says "no/nope/not interested" → value = "no"
   - This applies to yes/no question types
3. INFER the slot value even if they don't say it explicitly
4. Look for synonyms and related meanings:
   - "Islamic/Shariah/Halal" → banking_type: Islamic
   - "Conventional/Regular/Traditional" → banking_type: Conventional
   - "Education/Child/School/Study" → account_goal: Education
   - "Long-term/Wealth/Future/Retire" → account_goal: Wealth Building
   - "Monthly/Income/Regular" → account_goal: Monthly Income
   - "Emergency/Safety/Rainy day" → account_goal: Emergency Fund
   - "Short-term/Quick/3-6 months" → preferred_tenure: Short-term
   - "Medium/1-2 years" → preferred_tenure: Medium-term
   - "Long-term/5+ years" → preferred_tenure: Long-term
   - "Premium/High/Best/9.75%" → premium_returns: Yes
   - "Highest/Maximum rates" → premium_returns: Yes
5. If the user mentions a NUMBER for deposit/amount, extract it
6. If UNCLEAR or NOT mentioned, return null
7. Be AGGRESSIVE in extraction - assume user is helping us understand their need

CONFIDENCE SCORING:
- 1.0 = Explicitly stated by user OR direct yes/no to current question
- 0.7-0.9 = Strong inference from context
- 0.4-0.7 = Reasonable inference but could be wrong
- 0.0-0.4 = Weak signal, probably shouldn't extract

Return JSON:
{{
    "value": "<extracted value or null>",
    "confidence": <0.0-1.0>,
    "reasoning": "<1 line explanation>"
}}

Return ONLY valid JSON, no markdown."""

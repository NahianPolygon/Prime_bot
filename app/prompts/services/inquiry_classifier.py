INQUIRY_CLASSIFICATION_PROMPT = """Analyze this banking user message and classify it. Return JSON with these fields:
- inquiry_type: one of [PRODUCT_INFO_QUERY, COMPARISON_QUERY, ELIGIBILITY_QUERY, GENERAL_QUESTION]
- confidence: 0.0-1.0
- banking_type: 'conventional' or 'islami' if mentioned, else null
- product_category: detected product type (credit_card, savings_account, deposit_scheme, loan, investment) if any, else null
- age: extracted age if mentioned, else null
- income: extracted annual income if mentioned, else null
- employment: employment type if mentioned, else null
- keywords: list of relevant banking keywords found
- reasoning: brief explanation

Message: "{user_message}"

Return ONLY valid JSON, no markdown or extra text."""
